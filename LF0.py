import boto3

#define the client to interact with Lex
client = boto3.client('lex-runtime')

def lambda_handler(event,context):
    msg_from_user = event['messages'][0]

    #get the text
    text = msg_from_user['unstructured']['text']


    #send it to Lex and get the response from Lex
    response = client.post_text(botName = 'testbot',
                                botAlias = 'greeting',
                                userId = 'testuser',
                                inputText = text)
    msg_from_lex = response['message']

    #display the response to frontend
    if msg_from_lex:
        resp = {
            'statusCode':200,
            'messages':[{
                'type': 'unstructured',
                'unstructured':{
                    'text':msg_from_lex
                }
            }]
        }
        return resp