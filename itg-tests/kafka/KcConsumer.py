import json,os
from confluent_kafka import Consumer, KafkaError


class KafkaConsumer:

    def __init__(self, kafka_env = 'LOCAL', kafka_brokers = "", kafka_user = "", kafka_password = "", topic_name = "",autocommit = True):
        self.kafka_env = kafka_env
        self.kafka_brokers = kafka_brokers
        self.kafka_user = kafka_user
        self.kafka_password = kafka_password
        self.topic_name = topic_name
        self.kafka_auto_commit = autocommit

    # See https://github.com/edenhill/librdkafka/blob/master/CONFIGURATION.md
    # Prepares de Consumer with specific options based on the case
    def prepareConsumer(self, groupID = "pythonconsumers"):
        options ={
                'bootstrap.servers':  self.kafka_brokers,
                'group.id': groupID,
                'auto.offset.reset': 'earliest',
                'enable.auto.commit': self.kafka_auto_commit,
        }
        if (self.kafka_env != 'LOCAL'):
            options['security.protocol'] = 'SASL_SSL'
            options['sasl.mechanisms'] = 'PLAIN'
            options['sasl.username'] = self.kafka_user
            options['sasl.password'] = self.kafka_password
        if (self.kafka_env == 'OCP'):
            options['sasl.mechanisms'] = 'SCRAM-SHA-512'
            options['ssl.ca.location'] = os.environ['PEM_CERT']

        # Printing out producer config for debugging purposes        
        print("[KafkaConsumer] - This is the configuration for the consumer:")
        print("[KafkaConsumer] - -------------------------------------------")
        print('[KafkaConsumer] - Bootstrap Server:  {}'.format(options['bootstrap.servers']))
        if (self.kafka_env != 'LOCAL'):
            # Obfuscate password
            if (len(self.kafka_password) > 3):
                obfuscated_password = self.kafka_password[0] + "*****" + self.kafka_password[len(self.kafka_password)-1]
            else:
                obfuscated_password = "*******"
            print('[KafkaConsumer] - Security Protocol: {}'.format(options['security.protocol']))
            print('[KafkaConsumer] - SASL Mechanism:    {}'.format(options['sasl.mechanisms']))
            print('[KafkaConsumer] - SASL Username:     {}'.format(options['sasl.username']))
            print('[KafkaConsumer] - SASL Password:     {}'.format(obfuscated_password))
            if (self.kafka_env == 'OCP'): 
                print('[KafkaConsumer] - SSL CA Location:   {}'.format(options['ssl.ca.location']))
        print("[KafkaConsumer] - -------------------------------------------")

        # Create the consumer
        self.consumer = Consumer(options)
        self.consumer.subscribe([self.topic_name])
    
    # Prints out and returns the decoded events received by the consumer
    def traceResponse(self, msg):
        msgStr = msg.value().decode('utf-8')
        print('[KafkaConsumer] - Consumed message from topic {} partition: [{}] at offset {}:'.format(msg.topic(), msg.partition(), msg.offset()))
        print('[KafkaConsumer] - key: {}, value: {}'.format(str(msg.key()), msgStr))
        return msgStr

    # Polls for events until it finds an event where keyId=keyname
    def pollNextEvent(self, keyID, keyname):
        gotIt = False
        anEvent = {}
        while not gotIt:
            msg = self.consumer.poll(timeout=10.0)
            # Continue if we have not received a message yet
            if msg is None:
                continue
            if msg.error():
                print("[KafkaConsumer] - Consumer error: {}".format(msg.error()))
                # Stop reading if we find end of partition in the error message
                if ("PARTITION_EOF" in msg.error()):
                    gotIt= True
                continue
            msgStr = self.traceResponse(msg)
            # Create the json event based on message string formed by traceResponse
            anEvent = json.loads(msgStr)
            # If we've found our event based on keyname and keyID, stop reading messages
            if (anEvent["payload"][keyname] == keyID):
                gotIt = True
        return anEvent

    # Polls for events until it finds an event with same key
    def pollNextEventByKey(self, keyID):
        if (str(keyID) == ""):
            print("[KafkaConsumer] - Consumer error: Key is an empty string")
            return None
        gotIt = False
        anEvent = {}
        while not gotIt:
            msg = self.consumer.poll(timeout=10.0)
            # Continue if we have not received a message yet
            if msg is None:
                continue
            if msg.error():
                print("[KafkaConsumer] - Consumer error: {}".format(msg.error()))
                # Stop reading if we find end of partition in the error message
                if ("PARTITION_EOF" in msg.error()):
                    gotIt= True
                continue
            msgStr = self.traceResponse(msg)
            # Create the json event based on message string formed by traceResponse
            anEvent = json.loads(msgStr)
            # If we've found our event based on keyname and keyID, stop reading messages
            if (str(msg.key().decode('utf-8')) == keyID):
                gotIt = True
        return anEvent

    # Polls for events endlessly
    def pollEvents(self):
        gotIt = False
        while not gotIt:
            msg = self.consumer.poll(timeout=10.0)
            if msg is None:
                continue
            if msg.error():
                print("[ERROR] - [KafkaConsumer] - Consumer error: {}".format(msg.error()))
                if ("PARTITION_EOF" in msg.error()):
                    gotIt= True
                continue
            self.traceResponse(msg)
    
    def close(self):
        self.consumer.close()