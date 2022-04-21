import boto3
import dateutil
import datetime
import time
import os
import json

greetings = ['how are you','hello','hi']

city_range = ['new york','manhattan','manhattan area']
cuisine_range = ['indian','korean','chinese','japanese','american','italian','buffet','brunch','thai']

thankyou = ['thanks','thanks a lot','thank','thank you','bye','great']


#construct the error message
def construct(message,slot):
    return {'slot':slot, 'message':{'contentType':'PlainText','content':message}}

def validation(city,cuisine,number,date,time,phone,email):
    #validate the city input
    if city and city.lower() not in city_range:
        return construct('We currently only offer suggestions within New York or Manhattan area. Please try again.','city')

    #validate the cuisine input
    if cuisine and cuisine.lower() not in cuisine_range:
        return construct('We currently only offer suggestins in these types: Indian, Korean, Chinese, American, Japanese, Italian, Buffet, Brunch, Thai. Please try again','cuisine')

    #validate the number of number_of_people
    if number and not (0 < int(number) <= 8):
        return construct('Please enter a number between 1 and 8 inclusive.','numberofpeople')

    #validate the date
    if date:
        try:
            dateutil.parser.parse(date)
            d = datetime.datetime.strptime(date, '%Y-%m-%d').date()
            if d < datetime.date.today():
                return construct('Please enter a valid date.','date')
        except:
            return construct('Please enter the date in the format yyyy/mm/dd.','date')

    #we don't need to validate time, since lex has already checked for us

    #for the same reason, we don't need to validate the email address, lex done for us.
    #also, since we have move the account out of the sandbox, so now we can send email to any address in us-east-1
    
        
    #validate phone_number
    if phone and len(phone) != 10:
        return construct('Please enter a valid 10 digits US phone number','phonenumber')
    

    #if pass all validations
    return construct(None,None)



#elicit the slot
def elicit(sessionAttributes,intentName,slots,slotToElicit,message):
    return {'sessionAttributes':sessionAttributes,
            'dialogAction':{
                'type': 'ElicitSlot',
                'intentName': intentName,
                'slots':slots,
                'slotToElicit':slotToElicit,
                'message':{'contentType':'PlainText','content':message}
                }
            }

#delegate
def delegate(sessionAttributes,slots):
    return {'sessionAttributes':sessionAttributes,
            'dialogAction':{
                'type':'Delegate',
                'slots':slots
                }
            }


# fulfillment
def close(sessionAttributes,message):
    return{
            'sessionAttributes':sessionAttributes,
            'dialogAction':{
                'type':'Close',
                'fulfillmentState':'Fulfilled',
                'message':{'contentType':'PlainText','content':message}
                }
        }



def suggestionIntent(intent):
    #get the user input
    city = intent['currentIntent']['slots']['city']
    cuisine = intent['currentIntent']['slots']['cuisine']
    number_of_people = intent['currentIntent']['slots']['numberofpeople']
    date = intent['currentIntent']['slots']['date']
    time = intent['currentIntent']['slots']['time']
    phone_number = intent['currentIntent']['slots']['phonenumber']
    e_mail = intent['currentIntent']['slots']['email']

    # get the sessionAttributes
    sessionAttributes = intent['sessionAttributes']
    if not sessionAttributes:
        #construct it
        sessionAttributes = {}

        currentReservation = {'city':city,
                              'cuisine':cuisine,
                              'numberofpeople':number_of_people,
                              'date':date,
                              'time':time,
                              'phonenumber':phone_number,
                              'email':e_mail
            
        }


        sessionAttributes['currentReservation'] = json.dumps(currentReservation)

    #get the attributes
    currentReservation = {  'city':city,
                            'cuisine':cuisine,
                            'numberofpeople':number_of_people,
                            'date':date,
                            'time':time,
                            'phonenumber':phone_number,
                            'email':e_mail
                        }

    # get the sourse
    source = intent['invocationSource']

    if source == 'DialogCodeHook':
        # go to validation
        checkResult = validation(city,cuisine,number_of_people,date,time,phone_number,e_mail)

        #get the 'slots'
        slots = intent['currentIntent']['slots']

        # if validation fails
        if checkResult['slot']:
            # get the error slot and error message
            errorSlot = checkResult['slot']
            errorMessage = checkResult['message']['content']
            # clear the wrong user input in lex
            slots[errorSlot] = None

            #elicit the error slot again
            return elicit(sessionAttributes,intent['currentIntent']['name'],slots,errorSlot,errorMessage)

        # validation pass, delegate lex to prompt next question
        return delegate(sessionAttributes,slots)

    #push the user input to Q1
    messageID = send_to_sqs(currentReservation)
    print (messageID)
    print('successfull push message into sqs')


    #fulfillment

    return close(sessionAttributes,'You’re all set. Expect my suggestions shortly by email! Have a nice day!')



def greatIntent(intent):
    # validate the input
    if (intent["inputTranscript"]).lower() in greetings:
        #fulfill the intent
        return {"dialogAction": {
                "type": "Close",
                "fulfillmentState": "Fulfilled",
                "message": {
                    "contentType": "PlainText",
                    "content": "Hi there, I am your restaurant suggestion bot. how can I help?"
                    }
                }
            }

def thankIntent(intent):
    # validate the input
    if (intent["inputTranscript"]).lower() in thankyou:
        #fulfill the intent
        return {"dialogAction": {
                "type": "Close",
                "fulfillmentState": "Fulfilled",
                "message": {
                    "contentType": "PlainText",
                    "content": "You are welcome."
                    }
                }
            }

# push the input to sqs
def send_to_sqs(currentReservation):
    print('ready to connect sqs')
    client = boto3.client('sqs')
    attributes = {
        "city": {
                "DataType": 'String',
                'StringValue': currentReservation['city']
            },
        'cuisine': {
            'DataType': 'String',
            'StringValue': currentReservation['cuisine']
        },
        "number_of_people": {
            "DataType": "Number",
            'StringValue': currentReservation['numberofpeople']
        },
        "date": {
            'DataType': "String",
            'StringValue': currentReservation['date']
        },
        "time": {
            'DataType': "String",
            'StringValue': currentReservation['time']
        },
        "phone_number":{
            'DataType': "String",
            'StringValue': currentReservation['phonenumber']
        },
        "e_mail": {
            'DataType' : "String",
            'StringValue' : currentReservation['email']
        }
    }

    response = client.send_message(
            QueueUrl = 'https://sqs.us-east-1.amazonaws.com/059614236999/Q1',
            MessageAttributes = attributes,
            MessageBody = ('User Preference')
    )


    return response['MessageId']


def lambda_handler(event,context):
    os.environ['TZ'] = 'US/Eastern'
    time.tzset()

    #check the current intent's name
    intent = event['currentIntent']['name']

    #validate and fulfill the user input for greeting intent
    if intent == 'greetingintent':
        return greatIntent(event)


    #validate and fulfill the user input for dinning suggestion intent
    if intent == 'DiningSuggestionIntent':
        return suggestionIntent(event)

    #validate and fulfill the user input for thankyou intent
    if intent == 'thankyouintent':
        return thankIntent(event)