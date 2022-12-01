import tweepy
import keys as tokens
import sys
from git import Repo
import os
import datetime

delivery_date = datetime.date.today()+datetime.timedelta(days = 1)

path = ''
if 'win' in sys.platform:
    try:
        p = os.path.abspath(__file__).split('\\')
        path = '{}/'.format('/'.join(p[0:len(p)-1]))
        print('windows '+path)
        os.chdir(path)
    except:
        print('running from spyder, working folder is {}'.format(os.getcwd()))


if 'linux' in sys.platform:
    try:
        p = os.path.abspath(__file__).split('/')
        path = '{}/'.format('/'.join(p[0:len(p)-1]))
        print('linux '+path)
        os.chdir(path)
    except:
        print('running from spyder, working folder is {}'.format(os.getcwd()))

# Authorize our Twitter credentials
auth = tweepy.OAuthHandler(tokens.APIKey, tokens.APISecret)
auth.set_access_token(tokens.AccessToken, tokens.AccessSecret)
api = tweepy.API(auth)

userID = 'EWeerbericht'

tweets = api.user_timeline(screen_name=userID,
                           # 200 is the maximum allowed count
                           count=10,
                           include_rts = False,
                           # Necessary to keep full_text
                           # otherwise only the first 140 words are extracted
                           tweet_mode = 'extended'
                           )

for tweet in tweets:
    if 'Prijscurve voor morgen!' in tweet._json['full_text']:
        tweet = tweet._json
        break

with open (path+'lastcopy.txt', 'r') as f:
    lines = f.readlines()
    f.close()

tweet_id = tweet['id']

alreadytweeted = False
if tweet_id == int(lines[0]):
    alreadytweeted = True

if not alreadytweeted:
    '''
    media_url = tweet['entities']['media'][0]['expanded_url']
    media_url = media_url[0:len(media_url)-1]+'2'
    media_id = tweet['entities']['media'][0]['id']
    '''
    filename = 'figs/forecast_'+delivery_date.strftime('%d%m%Y')+'.png'
    imgs = []
    media = api.media_upload(filename)
    imgs.append(media.media_id_string)
    os.remove(filename)
    
    tweet_url = 'https://twitter.com/EWeerbericht/status/'+str(tweet_id)
    client = tweepy.Client(consumer_key=tokens.APIKey,
                           consumer_secret=tokens.APISecret,
                           access_token=tokens.AccessToken,
                           access_token_secret=tokens.AccessSecret)
    initial_tweet = client.create_tweet(text = 'Het energieweerbericht voor morgen!', media_ids = imgs)

    twid = initial_tweet.data['id']
    reply = client.create_tweet(text=tweet_url, in_reply_to_tweet_id=twid)

    with open (path+'lastcopy.txt', 'w') as f:
        line = str(tweet_id)
        f.write(line)
        f.close()

    repo = Repo(path)
    repo.index.add('lastcopy.txt')
    repo.index.commit('autocommit tweet {}'.format(str(datetime.date.today())))
    origin = repo.remotes[0]
    origin.push()
