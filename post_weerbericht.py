import tweepy
import keys as tokens
import scrape as s

tweet = s.tweet

auth = tweepy.OAuthHandler(tokens.APIKey, tokens.APISecret)
auth.set_access_token(tokens.AccessToken, tokens.AccessSecret)
api = tweepy.API(auth)

client = tweepy.Client(consumer_key=tokens.APIKey,
                       consumer_secret=tokens.APISecret,
                       access_token=tokens.AccessToken,
                       access_token_secret=tokens.AccessSecret)

client.create_tweet(text = tweet)
