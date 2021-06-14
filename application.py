import logging
import flask
from flask import request, Response
import os
from boto3 import client
from sentence_transformers import SentenceTransformer
import torch
import torch.nn as nn

# Create and configure the Flask app
application = flask.Flask(__name__)
os.environ['APP_CONFIG'] = 'default_config'
application.config.from_envvar('APP_CONFIG', silent=True)
application.debug = application.config['FLASK_DEBUG'] in ['true', 'True']

ddb = client('dynamodb', region_name=application.config['AWS_REGION'])


sts = SentenceTransformer('sentence-transformers/distilbert-multilingual-nli-stsb-quora-ranking')
cos = nn.CosineSimilarity(dim=0, eps=1e-6)


@application.route('/match_reply_to_topic', methods=['POST'])
def match_reply_to_topic():
    response = None
    if request.json is None:
        # Expect application/json request
        response = Response("", status=415)
    else:
        try:
            reply_data = {k: v for k, v in request.json.items()}
            logging.warning('reply: ' + str(reply_data))
            reply_embeds = torch.tensor(sts.encode(reply_data['text']))

            topics = get_topics()
            match_topic = max(
                topics,
                key=lambda x: cos(torch.tensor(sts.encode(x['topic'])), reply_embeds)
            )
            logging.warning('matched topic: ' + str(match_topic))

            write_reply_to_ddb(reply_data, match_topic)
            publish_to_frontend(reply_data, match_topic)
            response = Response("", status=200)
        except Exception as ex:
            logging.exception('Error processing message: %s' % request.json)
            response = Response(ex.message, status=500)

    return response

def get_topics():
    items = ddb.scan(TableName=application.config['TOPIC_TABLE_NAME'])
    topics = [{k: v['S'] for k, v in item.items()} for item in items['Items']]
    return topics

def write_reply_to_ddb(reply_data, match_topic):
    pass

def publish_to_frontend(reply_data, match_topic):
    pass

if __name__ == '__main__':
    application.run(host='0.0.0.0')