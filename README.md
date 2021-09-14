Automating IT Help Desk with Self-Service Chatbot and WhatsApp API and Twilio Flex
![image](https://user-images.githubusercontent.com/40875938/133207274-b0d401dd-7a1a-407f-9b2e-7217a9f1206e.png)


# **Improve Call Center productivity with life-like conversational Chatbot**
## **Objective:** 
The purpose of the document is to build applications with highly engaging user experiences and lifelike conversational interactions using Amazon Chatbot to increase contact center productivity, automate simple tasks, and drive operational efficiencies across the enterprise with Twilio WhatsApp Business API, SMS and Flex.

## **High Level steps**
1. ### Sign up or log in  [Twilio](https://www.twilio.com/console) Account and get a Twilio Phone number
**Connect Twilio Phone number with WhatsApp Sandbox Setting –** The Twilio Sandbox for WhatsApp is a pre-configured environment available through the Twilio Console in which you can prototype sending outbound messages, replying to incoming messages, and configuring things like message delivery callbacks. The Sandbox is pre-provisioned with a Twilio phone number (+1-415-523-8886) that is shared across all sandbox users. However, other users who share the same sandbox number won't receive your messages, only the ones who have opted in to your sandbox.

Go to Messaging --> Settings -->  WhatsApp SandBox Setting. Send a WhatsApp message to +1 415 523 8886 with code “join xxxxxxxxx” as shown in your account. You will receive a message back in your WhatsApp i.e. “Twilio Sandbox: ✅ You are all set! The sandbox can now send/receive messages from whatsapp:+14155238886. Reply stop to leave the sandbox any time.”

![](Aspose.Words.d672e59f-f91e-4ac4-b704-f109e33c8b96.002.png)
2. **Create a new Twilio [Flex](https://www.twilio.com/console/projects/create?g=/console/flex/setup&t=96e837a3b43a8c7981af899eaae92b968887485e3f454d330a821ab7c8738d5e) Account**

Follow the prompts to kick off the Flex setup. During this process, several Twilio services will be created for you. Launch the Flex UI in chrome browser, and you should see something like this.

![image](https://user-images.githubusercontent.com/40875938/133193617-27698464-de75-409d-b293-9ec17f9ae276.png)

Construct a Message Handler URL. The format of your Messaging Handler URL should be:
https://webhooks.twilio.com/v1/Accounts/ACxx/Proxy/KSxx/Webhooks/Message

Replace ACxx with your Account SID (found [in your account dashboard](https://www.twilio.com/console)) and KSxx with your Flex Proxy Service SID (found [in the Services page](https://www.twilio.com/console/proxy/services)). This will be your Message Handler URL.
##
Set up your WhatsApp Sandbox:   Navigate to the [WhatsApp Sandbox](https://www.twilio.com/console/sms/whatsapp/sandbox).  Head over to the [Sandbox Configuration](https://www.twilio.com/console/sms/whatsapp/sandbox) section and paste the Message Handler URL into the "When A Message Comes In" text field. Save your sandbox settings.
## ![WhatsApp Sandbox webhook setup](https://twilio-cms-prod.s3.amazonaws.com/images/jRf5uNLU\_ma2REupARpo-\_FhZNmLXoFMc5e2QSfpiR1pII.width-800.png)
##
3. ### Clone the [git repository](https://github.com/purnasanyal/WhatsApp.git) in your local laptop or desktop

git clone <https://github.com/purnasanyal/WhatsApp.git>

4. ### Sign Up for an [AWS Account](https://docs.aws.amazon.com/lexv2/latest/dg/gs-account.html), create IAM user and Provide IAM admin role

If you already have AWS Account and AWS user, please ensure that the user has admin privilege to create all AWS resources for this application.

5. ### Create S3 Bucket in us-east-1 region
- Copy all folders under “assets” folder in the github repo. Write down the S3 bucket name
  - Faq
  - lambda\_layers
  - lex-appointment-handler
  - lex\_bot
  - lex\_custom\_resource
  - twilio-webhook-lambda
- Copy CloudFormation template “WhatsApp.yaml” in the S3 bucket

6. ### Launch a new CloudFormation stack in us-east-1 region

Click “Launch Stack” Button and deploy the application:

[![cloudformation-launch-stack](https://s3.amazonaws.com/cloudformation-examples/cloudformation-launch-stack.png)](https://console.aws.amazon.com/cloudformation/home?region=us-east-1#/stacks/create/template)

![image](https://user-images.githubusercontent.com/40875938/133193922-9d5fc723-e8ea-40ea-b3c3-ad5170fcad3c.png)

- Click “Template is ready” and “Amazon S3 URL”. Provide Amazon S3 URL path of  WhatsApp.yaml template
- Provide a stack name e.g. “ps-twilio”
- Replace the “S3BucketName” parameters with the S3 bucket you created in step 5. Leave other parameter value as the default value and create CloudFormation stack.
- The stack creation may take up to 10 min
- CloudFormation Stack will create Amazon Lex Bot, Kendra Indexes and Lambda function to perform initialization and validation, fulfillment of Lex Bot intent configuration.
7. ### Copy URL to “WHEN A MESSAGE COMES IN” field of Twilio Sandbox for WhatsApp

Once the CloudFormation stack is complete, copy & paste the output value for CustomWebhookHandlerEndpoint URL into “WHEN A MESSAGE COMES IN” field of Twilio Sandbox for WhatsApp account, you created in Step 1. 

![](Aspose.Words.d672e59f-f91e-4ac4-b704-f109e33c8b96.005.png)


## **Test the Chatbot and the application**
Open Whatsapp in Mobile phone or web version and send message to +14155238886  to test the following scenarios from WhatsApp

1. Greetings Message – type and send message  “hi” 
1. Schedule an appointment -  type and send message  “Schedule”
1. Confirm an appointment  - type and send message  “confirm”
1. Standard Frequently asked questions - type and send any question from covid-faq.csv
1. Connect to Twilio Flex Contact Center - type and send message  “talk to an agent”
1. Voice Call from Support Agent – Place outbound call from Twilio Flex

![](Aspose.Words.d672e59f-f91e-4ac4-b704-f109e33c8b96.006.png)
