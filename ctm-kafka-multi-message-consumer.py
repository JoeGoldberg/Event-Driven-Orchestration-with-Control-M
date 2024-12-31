#!/usr/bin/env python3.11 -u

import argparse
import json
import boto3
from kafka import KafkaConsumer
from jinja2 import Template
import requests
from datetime import datetime
import threading
import io

verify_certs = True
#   For debugging
#    import pdb;pdb.set_trace()

def parse_arguments():
    parser = argparse.ArgumentParser(description="Consume Kafka messages and create Control-M jobs")
    parser.add_argument("-b", "--bucket", required=False, default="623469066856-ctmprod-templates",help="S3 bucket name (also used as Secrets Manager secret name)")
    parser.add_argument("-s", "--ctm-server", required=False, default="smprod",help="Control-M server name")
    parser.add_argument("-r", "--retention-days", type=int, required=False, default=14, help="Number of days to retain jobs")
    parser.add_argument("-n", "--num-pairs", type=int, required=False, default=2, help="Number of event pairs to process - not implemented yet")
    return parser.parse_args()

def get_s3_object(bucket, key):
    s3 = boto3.client('s3', region_name='us-west-2')
    response = s3.get_object(Bucket=bucket, Key=key)
    return response['Body'].read().decode('utf-8')

def get_template_from_s3(bucket, key):
    return get_s3_object(bucket, key)

def get_ctm_constants(secret_name):
    session = boto3.session.Session()
    client = session.client(service_name='secretsmanager', region_name='us-west-2')
    
    try:
        get_secret_value_response = client.get_secret_value(SecretId=secret_name)
    except Exception as e:
        raise e
    else:
        if 'SecretString' in get_secret_value_response:
            secret = get_secret_value_response['SecretString']
            return json.loads(secret)
        else:
            raise ValueError("Secret not found or not in the expected format")

def check_job_exists(job_name, ctm_constants):
    headers = {'x-api-key': ctm_constants['CTM_API_KEY']}
    jobs_url = f"{ctm_constants['CTM_API_BASE_URL']}/run/jobs/status"
    today_date = datetime.today().strftime('%y%m%d')
    jobs_search = {"jobname": job_name, "orderFromDate" : today_date}
    response = requests.get(jobs_url, headers=headers, params=jobs_search, verify=verify_certs)

    response.raise_for_status()
    jobs = json.loads(response.text)
    num_jobs= int(jobs['returned'])
    return num_jobs

def submit_job_to_controlm(json_payload, ctm_constants):
    headers = {'x-api-key': ctm_constants['CTM_API_KEY']}
    run_url = f"{ctm_constants['CTM_API_BASE_URL']}/run"
    
    # Convert JSON payload to file-like object
    job_json_stream = io.StringIO(json_payload)
    files = {'jobDefinitionsFile': ('jobs.json', job_json_stream, 'application/json')}
    
    response = requests.post(run_url, files=files, headers=headers, verify=verify_certs)
    response.raise_for_status()

    return response.json()

def process_parent_event(message, args, ctm_constants):
    parent_id = message['id']
    job_name = f"prnt-{parent_id}"
    now = datetime.now()
    current_time = now.strftime("%H:%M:%S")
    print(current_time + " " + "Processing parent message " + parent_id)

#    import pdb;pdb.set_trace()

    if check_job_exists(job_name, ctm_constants):
        raise Exception(f"Job {job_name} already exists for the current day")

    template_str = get_template_from_s3(args.bucket, 'parents/parent_template.json')
    template = Template(template_str)
    rendered_payload = json.loads(template.render(
        server_name=args.ctm_server,
        retention_days=args.retention_days,
        job_name=job_name,
        parentid=parent_id,
        ctmsla="23:59"
    ))

    json_payload = json.dumps(rendered_payload)

    now = datetime.now()
    current_time = now.strftime("%H:%M:%S")
    print(current_time + " " + "Submitting workflow for parent message " + parent_id)

    return submit_job_to_controlm(json_payload, ctm_constants)

def process_child_event(message, args, ctm_constants):
    parent_id = message['parent_id']
    parent_job_name = f"prnt-{parent_id}"
    child_job_name = f"child-{parent_id}"
    now = datetime.now()
    current_time = now.strftime("%H:%M:%S")
    print(current_time + " " + "Processing child message for parent " + parent_id)

#    import pdb;pdb.set_trace()

    if not check_job_exists(parent_job_name, ctm_constants):
        process_no_parent(parent_id, args, ctm_constants)

    template_str = get_template_from_s3(args.bucket, 'children/child_template.json')
    template = Template(template_str)
    rendered_payload = json.loads(template.render(
        server_name=args.ctm_server,
        retention_days=args.retention_days,
        job_name=child_job_name,
        parentid=parent_id,
        parent_job_name=parent_job_name
    ))

    json_payload = json.dumps(rendered_payload)

    now = datetime.now()
    current_time = now.strftime("%H:%M:%S")
    print(current_time + " " + "Submitting workflow for child message " + parent_id)

    return submit_job_to_controlm(json_payload, ctm_constants)

def process_no_parent(parent_id, args, ctm_constants):
    job_name = f"prnt-{parent_id}"
    template_str = get_template_from_s3(args.bucket, 'parents/parent_template.json')
    template = Template(template_str)
    rendered_payload = json.loads(template.render(
        server_name=args.ctm_server,
        retention_days=args.retention_days,
        job_name=job_name,
        parentid=parent_id,
        ctmsla="23:59"

    ))

    json_payload = json.dumps(rendered_payload)

    return submit_job_to_controlm(json_payload, ctm_constants)

def process_topic(topic_name, process_func, args, ctm_constants):
    consumer = KafkaConsumer(topic_name, bootstrap_servers=['localhost:9092'])
    for message in consumer:
        try:
            event = json.loads(message.value)
            process_func(event, args, ctm_constants)
        except Exception as e:
            print(f"Error processing {topic_name} event: {e}")

def main():
    args = parse_arguments()
    ctm_constants = get_ctm_constants(args.bucket)  # Using bucket name as secret name

    print("Listening for parents and children")

    parent_thread = threading.Thread(target=process_topic, args=('ctm-parent-events', process_parent_event, args, ctm_constants))
    children_thread = threading.Thread(target=process_topic, args=('ctm-children-events', process_child_event, args, ctm_constants))

    parent_thread.start()
    children_thread.start()

    parent_thread.join()
    children_thread.join()

if __name__ == "__main__":
    main()

