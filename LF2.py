
import boto3
from requests_aws4auth import AWS4Auth
from opensearchpy import OpenSearch, RequestsHttpConnection
import json
from botocore.exceptions import ClientError


# go to opensearch to search 3 results by cuisine name
def opensearch_result(cuisine):
    
    # connect to opensearch
    print('ready to connect openSearch')
    
    host = 'search-restaurants-crhg6s6m3rbs7uvjajerqp6y4q.us-east-1.es.amazonaws.com'
    region = 'us-east-1'
    service = 'es'
    
    # get the credentials
    credentials = boto3.Session().get_credentials()
    awsauth = AWS4Auth(credentials.access_key, credentials.secret_key, region, service, session_token=credentials.token)

    opensearch = OpenSearch(
        hosts = [{'host': host, 'port': 443}],
        http_auth = awsauth,
        verify_certs = True,
        use_ssl = True,
        connection_class = RequestsHttpConnection
    )
    print('enter opensearch success')
    
    # search for 3 matches
    result = opensearch.search(size = 3, index = 'restaurants', body={"query": {"match": {'Cuisine':cuisine}}})
    print(result)
    
    #follow the opesearch response result's structure to retrieve restaurant ID
    hits=result['hits']['hits']
    print(hits)
    
    ids = list(map(lambda x: x['_id'], hits))
    print(ids)
    
    return ids


def get_complete(ids, cuisine, number_of_people, date, time):
    # connect to dynamoDB
    print('ready to connect to dynamodb')
    dynamodb = boto3.resource('dynamodb', region_name='us-east-1')
    table = dynamodb.Table('yelp-restaurants')
    print('successful enter DB')
    
    #construct the response
    res = "Hello!\nHere are my "+cuisine+" restaurants suggestions for "+number_of_people+" people, for "+date+" at "+time+": \n\n"


    for i in range(len(ids)):
        response = table.get_item(
            Key={
                'business ID': ids[i]
            }
        )

        item = response['Item']
        name = item['name']
        address = item['address']
        rating = str(item['rating'])
        res += str(i+1)+"." +name+", located at "+address+", rating "+rating+".\n"

    res += '\nEnjoy your meal! '
    
    print(res)

    return res


def send_email(To_address,details):
    print('ready to enter SES')
    
    SENDER = "ChatBot <hz2759@columbia.edu>"

    RECIPIENT = To_address

    AWS_REGION = "us-east-1"

    SUBJECT = "Your Dining Suggestion"

    # The email body for recipients with non-HTML email clients.
    BODY_TEXT = details

    CHARSET = "UTF-8"

    # Create a new SES resource and specify a region.
    client = boto3.client('ses',region_name=AWS_REGION)

    # Try to send the email.
    try:
        #Provide the contents of the email.
        response = client.send_email(
            Destination={
                'ToAddresses': [
                    RECIPIENT,
                ],
            },
            Message={
                'Body': {
                    'Text': {
                        'Charset': CHARSET,
                        'Data': BODY_TEXT,
                    },
                },
                'Subject': {
                    'Charset': CHARSET,
                    'Data': SUBJECT,
                },
            },
            Source=SENDER,

        )
    # Display an error if something goes wrong.
    except ClientError as e:
        print(e.response['Error']['Message'])
    else:
        print("Email sent! Message ID:"),
        print(response['MessageId'])




def lambda_handler(event, context):
    # connect to sqs to retrieve the message
    print('enter sqs')
    client = boto3.client('sqs')
    Queue_url = 'https://sqs.us-east-1.amazonaws.com/059614236999/Q1'
    print('success enter sqs')

    # message poll from  Q1
    message = client.receive_message(QueueUrl = Queue_url, MessageAttributeNames=['All'])
    print(message)


    try:
        # follow the sqs messages structure to retrieve information we need
        
        # use receipt handle to delete message later
        ReceiptHandle = message['Messages'][0]['ReceiptHandle']
        
        MessageAttributes = message['Messages'][0]['MessageAttributes']
        
        city = MessageAttributes['city']['StringValue']

        cuisine = MessageAttributes['cuisine']['StringValue']
        
        number_of_people = str(MessageAttributes['number_of_people']['StringValue'])
        
        date = MessageAttributes['date']['StringValue']
        
        time = MessageAttributes['time']['StringValue']
        
        phone_number = MessageAttributes['phone_number']['StringValue']

        email = MessageAttributes['e_mail']['StringValue']
        
        print(city,cuisine,number_of_people,date,time,phone_number,email)

        # the result from openSearch
        ids = opensearch_result(cuisine)
        print('successful search from openSearch')


        # retrieve complete information from dynamoDB
        complete_info = get_complete(ids, cuisine, number_of_people, date, time)


        send_email(email, complete_info)


        # delete the message from sqs
        client.delete_message(
                QueueUrl=Queue_url,
                ReceiptHandle=ReceiptHandle
            )
        print('successful delete the message')

    except Exception as e:
        print(e)