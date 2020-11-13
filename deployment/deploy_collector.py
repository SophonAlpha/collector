"""
Master script for the deployment of the TfL Bike Sharing collector application.
"""

import boto3
from deployment.cloudformationtools import cloudformationtools

profile_deployment_account = 'workaccount'
profile_DNS_account = 'dns_account'

# ----- deploy collector server
print('Deploying stack for collector application.')
cf_session = boto3.session.Session(profile_name=profile_deployment_account).client('cloudformation')
response = cf_session.create_stack(
    StackName='Collector',
    TemplateURL='https://collector-deployment-bucket-m1mgfnap.s3-eu-west-1.amazonaws.com/deployment/Collector.yaml',
    Capabilities=['CAPABILITY_IAM']
)
stack_status = cloudformationtools.monitor_stack_deployment(cf_session, 'Collector')
print(f'Stack deployment completed with stack status: {stack_status}')

# ----- get collector server IP4 DNS name
response = cf_session.describe_stacks(
    StackName='Collector',
)
collector_server_IP4_DNS = [entry['OutputValue']
                            for entry in response['Stacks'][0]['Outputs']
                            if entry['OutputKey'] == 'CollectorServerIP4DNS'][0]
print(f'Collector server IP4 DNS name: {collector_server_IP4_DNS}')

# ----- add collector server name to DNS hosted zone
print('Updating Route53 DNS hosted zone with collector server IP4 DNS name.')
route53_session = boto3.session.Session(profile_name=profile_DNS_account).client('route53')
response = route53_session.change_resource_record_sets(
    HostedZoneId='Z3D8FUO7197SS3',
    ChangeBatch={
        'Comment': 'update record with EC2 instance public IPv4 DNS',
        'Changes': [
            {
                'Action': 'UPSERT',
                'ResourceRecordSet': {
                    'Name': 'sagittarius.eurydika.de.',
                    'Type': 'CNAME',
                    'TTL': 300,
                    'ResourceRecords': [
                        {
                            'Value': collector_server_IP4_DNS
                        },
                    ],
                }
            },
        ]
    }
)
print(f'Route53 DNS hosted zone update completed with '
      f'HTTP status code: {response["ResponseMetadata"]["HTTPStatusCode"]}')

print(f'Waiting for URL https://sagittarius.eurydika.de:3000/ to become active ... ')
response = cloudformationtools.wait_for_url('https://sagittarius.eurydika.de:3000/', 300)
print(f'URL check returned HTTPS code: {response}')
