# Event-Driven-Orchestration-with-Control-M
This git repository provides a sample implementation for a multi-event orchestration pattern in which work is triggered by multiple related events that occur on separate topics, arriving at separate times.
## Audience
This session is intended for data engineers, orchestration/automation architects and anyone who participates in, or is responsible for, managing workflows that support production workloads.

# Objective
Organizations are developing applications with complex event processing that requires interaction with orchestrated workflows. This scenario demonstrates an implementation using Kafka and Control-M that:
*  Processes multiple event "bundles" that result in a single workflow
*  Visualize all events within Control-M
*  Monitor for an SLA within which the entire event package should complete
*  Notify when either processing failures occur or event generation deviates from expectations
*  Persist events and event bundles for as long as required
*  Gain the ability to restart processing when either errors occur or event bundles are not generated as expected
*  Collect all execution history for event processing in Control-M Workload Archiving

# Description
This example implements a scenario in which a business transaction consists of two phases. This may be a proposal and an acceptance of a contract, for example an initial bid at a particular price that fluctuates and the acceptance of the proposal or any similar multi-part transaction.
   1. The ctm-kafka-paired-producer.py plays the role of our application that generates events as part of the transaction process. The initial transaction generates an event that is designated the parent. The subsequent event is a child. The relationship between the two is indicated by a parent-id field in the child that contains the uuid of the parent. 
   1. The ctm-kafka-multi-message-consumer.py consumes messages and generates Control-M jobs that orchestrate the work required to process each transaction.
   1. The parent and child can arrive any time within a 24-hour period.
   1. An SLA Management job is part of the flow. This monitors the 24-hour SLA and alerts in the event one of the events do not arrive as required.
   1. The structure of the workflow is defined in a Jinja template fetched from an S3 bucket. Samples are provided in the Github repo.
   1. The dependencies among the Control-M jobs are based on the parent uuid. Looking at the "application" job (the actual work that is being done), one dependency is "parent-<uuid of parent>" and the other is "child-<uuid of parent>" expanding this structure to include multiple "children" is simple to accomplish as long as each child has both linkage to the parent and an indicator of it position in the chain of children (child 1, child 2, etc.). The dependencies simply reflect that relationship; e.g. "parent-<uuid of parent>", "child-1-<uuid of parent>",  "child-2-<uuid of parent>", etc.
   1. Credentials required to connect to Control-M are stored in an AWS SecretsManager secret and relies on ctm-kafka-multi-message-consumer.py running on an ec2 instance that has the required AWS permissions granted. In our scenario, this is provided via an IAM Role associated with the EC2 instance on which we are running.
   1. The Python code provided here, has been generated by Claude AI tool from Anthropic. The prompts that were submitted are also provided in the Github repo.
   1. The Control-M Automation API is used to submit all jobs. This was originally developed in an environment that did not support the "run ondemand" service and thus all folders that are submitted are also preserved in Control-M. The next revision of this sample will switch to the "run ondemand" service which will create the workflows dynamically only in the Monitoring environment. 
# Artifacts
   * Jinja templates:   These are JSON templates that are rendered when events are received, to create the JSON that is submitted to Control-M
   * claude prompt.txt: The prompt submitted to Claude.AI to generate the Python code
   * ctm-kafka-multi-message-consumer.py: This script consumes messages, generates workflows based on Jinja templates that are rendered with values provided as arguments and submitted to Control-M defined by the endpoint and credentials retrieved from AWS SecretsManager
   * ctm-kafka-paired-producer.py: this script produces a pair of events to two separate topics, introducing random delays. This script is just a mockup of an application that would normally produce such events.
   * event-driven-orchestration.json: This JSON runs the two Python scripts on a host where a local copy of Kafka is running. The two jobs each run one of the above Python scripts and are provided to simplify running this scenario. When this folder is run, specify PARM1 to "-n x" where "x" is the number of event pairs to generate.
   * event-driven-orchestration-variables.json: Update line 3 of this JSON to specify the number of event pairs to generate
# Running this scenario
   1. Deploy the jobs to Control-M: **ctm deploy event-driven-orchestration.json**
   1. use the "run" service to execute the scenario: **ctm run order smprod jog-event-driven-orchestration -f event-driven-orchestration-variables.json**
# Resources
   1. Automation API [documentation](https://documents.bmc.com/supportu/API/Monthly/en-US/Documentation/API_Intro.htm)
   2. [Video showing this implementation](https://www.dropbox.com/scl/fi/mw4sbfbqzdio2srjxe7m7/2024-12-16-Event-Driven-Orchestration-with-Control-M.mp4?rlkey=l0kin5cewbc7f7omm8f58c4ml&st=nzit5iba&dl=0) 
