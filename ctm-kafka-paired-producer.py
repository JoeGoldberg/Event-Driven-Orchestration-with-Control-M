#!/usr/bin/env python3.11 -u

from kafka import KafkaProducer
import json
import uuid
import time
import random
import datetime
import argparse

def create_producer(bootstrap_servers):
    """Create and return a Kafka producer instance."""
    return KafkaProducer(
        bootstrap_servers=bootstrap_servers,
        value_serializer=lambda v: json.dumps(v).encode('utf-8')
    )

def create_parent_message():
    """Create a parent message with a unique ID."""
    return {
        'id': str(uuid.uuid4()),
        'timestamp': datetime.datetime.now().isoformat(),
        'random_value': random.randint(1, 1000),
        'description': 'Parent event message'
    }

def create_child_message(parent_id):
    """Create a child message with its own ID and parent's ID."""
    return {
        'id': str(uuid.uuid4()),
        'parent_id': parent_id,
        'timestamp': datetime.datetime.now().isoformat(),
        'random_value': random.randint(1, 1000),
        'description': 'Child event message'
    }

def produce_message_pair(producer, parent_topic, child_topic):
    """Produce a pair of parent-child messages with random delay between them."""
    # Create and send parent message
    parent_msg = create_parent_message()
    producer.send(parent_topic, parent_msg)
    print(f"Produced to {parent_topic}: {parent_msg}")
    
    # Random delay between parent and child messages (30 sec to 3 min)
    delay = random.uniform(30, 180)
    print(f"Waiting {delay:.1f} seconds before sending child message...")
    time.sleep(delay)
    
    # Create and send child message
    child_msg = create_child_message(parent_msg['id'])
    producer.send(child_topic, child_msg)
    print(f"Produced to {child_topic}: {child_msg}")
    
    # Random delay before next pair (30 sec to 5 min)
    if delay := random.uniform(30, 300):
        print(f"Waiting {delay:.1f} seconds before next message pair...")
        time.sleep(delay)

def main():
    # Parse command line arguments
    parser = argparse.ArgumentParser(description='Produce paired messages to Kafka topics')
    parser.add_argument('-b', '--bootstrap-servers', 
                        default='localhost:9092',
                        help='Kafka bootstrap servers (default: localhost:9092)')
    parser.add_argument('-n', '--num-pairs',
                        type=int,
                        default=20,
                        help='Number of message pairs to produce (default: 20)')
    args = parser.parse_args()
    
    # Create Kafka producer
    producer = create_producer(args.bootstrap_servers)
    
    # Define topics
    parent_topic = 'ctm-parent-events'
    child_topic = 'ctm-children-events'
    
    try:
        print(f"Starting to produce {args.num_pairs} message pairs...")
        for i in range(args.num_pairs):
            print(f"Producing pair {i+1} of {args.num_pairs}")
            produce_message_pair(producer, parent_topic, child_topic)
            
        print("Finished producing all message pairs")
            
    except KeyboardInterrupt:
        print("Production interrupted by user")
    finally:
        producer.close()
        print("Producer closed")

if __name__ == "__main__":
    main()

