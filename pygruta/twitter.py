#
#   pygruta CMS
#   ttcdt <dev@triptico.com>
#
#   This software is released into the public domain.
#

#   Twitter support

from twython import Twython
import datetime, time, re

import pygruta


def twitter_api(gruta):
    c_key          = gruta.template("cfg_twitter_consumer_key")
    c_secret       = gruta.template("cfg_twitter_consumer_secret")
    a_token_key    = gruta.template("cfg_twitter_access_token_key")
    a_token_secret = gruta.template("cfg_twitter_access_token_secret")

    if c_key != "" and c_secret != "" and a_token_key != "" and a_token_secret != "":
        twitter = Twython(c_key, c_secret, a_token_key, a_token_secret)
    else:
        twitter = None
        gruta.log("INFO", "Twitter: not configured -- cannot continue")

    return twitter


def import_tweets(gruta, queries, ignore_from):
    """ Does a set of searches on Twitter and store the results as stories """

    twitter = twitter_api(gruta)

    if twitter is None:
        return

    for qs in queries:
        gruta.log("DEBUG", "Twitter: query '%s'" % qs)

        q = twitter.search(q=qs, tweet_mode='extended', src='typd')

        tweets = q["statuses"]
        tweets.reverse()

        for e in tweets:
            # get information from the tweet
            id          = e["id_str"]
            story_id    = "twitter-" + id
            full_text   = e["full_text"]
            screen_name = e["user"]["screen_name"]
            name        = e["user"]["name"]
            user_url    = "https://twitter.com/" + screen_name
            avatar      = e["user"]["profile_image_url"]
            created_at  = e["created_at"]
            lang        = e["lang"]

            # did we already store that?
            if gruta.story("tweets", story_id):
                gruta.log("DEBUG", "Twitter: '%s' exists" % story_id)
                continue

            # screenname to ignore?
            if screen_name.lower() in ignore_from:
                gruta.log("DEBUG", "Twitter: ignore '%s'" % (screen_name + " " + id))
                continue

            # convert date
            dt = datetime.datetime.strptime(e["created_at"],
                "%a %b %d %H:%M:%S +0000 %Y")
            date = dt.strftime("%Y%m%d%H%M%S")

            # tweet or retweet?
            rt = e.get("retweeted_status")

            if rt:
                rt_id          = rt["id_str"]
                rt_screen_name = rt["user"]["screen_name"]

                title = "Retweet from %s (@%s)" % (name, screen_name)

                url = "https://twitter.com/" + rt_screen_name + "/status/" + rt_id
                redir_url = user_url
                body_1 = "Retweet <a href=\"" + url + "\">[tweet]</a> from "
                op = "Retweet"

                gruta.log("INFO", "Twitter: new retweet from '%s'" % ("@" + screen_name))
            else:
                title = "Tweet from %s (@%s)" % (name, screen_name)

                url = "https://twitter.com/" + screen_name + "/status/" + id
                redir_url = url
                body_1 = "<a href=\"" + url + "\">Tweet</a> from "
                op = "Tweet"

                gruta.log("INFO", "Twitter: new tweet from '%s'" % ("@" + screen_name))

            # build the story body
            content  = "<h2>" + title + "</h2>\n"
            content += "<p><img src=\"" + avatar + "\"/>\n"
            content += body_1 + "<a href=\"" + user_url + "\">" + name + "</a> (@" + screen_name + "):</p>\n"
            content += "<blockquote>\n" + full_text + "\n</blockquote>\n<p></p>\n"

            story = gruta.new_story({
                "id":         story_id,
                "topic_id":   "tweets",
                "title":      title,
                "format":     "raw_html",
                "full_story": "1",
                "image":      avatar,
                "redir":      redir_url,
                "lang":       lang,
                "date":       date,
                "content":    content
                })

            gruta.save_story(story)

            gruta.notify("New " + op + ": " + redir_url)

        # wait a bit to avoid pissing off Twitter
        time.sleep(1)


def send_feed(gruta):
    """ Sends a blog feed to Twitter's user """

    # get api
    twitter = twitter_api(gruta)

    if twitter is None:
        return

    # get or create the twitter 'follower' (i.e. this user)
    uid = gruta.template("cfg_main_user")
    twitter_user = "twitter:%s" % gruta.template("cfg_twitter_user")
    follower = gruta.follower(uid, twitter_user)

    if follower == None:
        follower = gruta.new_follower({
            "id":       twitter_user,
            "user_id":  uid,
            "date":     gruta.today(),
            "context":  "",
            "ldate":    "",
            "network":  "twitter"
        })

    for s in reversed(list(gruta.feed())):

        story = gruta.story(s[0], s[1])

        # if the 'follower' has not seen this story...
        if follower.get("ldate") < story.get("date"):
            # get start time for this story
            t = time.time()

            # build the tweet

            # story title
            tweet = pygruta.boldify(story.get("title")) + "\n\n"

            # story body
            tweet += pygruta.special_uris(gruta, story.get("body"))

            # replace paragraph separators
            tweet = tweet.replace("</p><p>", "\n")

            tweet = tweet.replace("<li>", "\u2022 ")

            # delete the rest of HTML tags
            tweet = re.sub("<[^>]+>", "", tweet)

            # replace repeated newlines
            tweet = re.sub("\n{3,}", "\n\n", tweet)

            # prepend story URL
            tweet = gruta.shorten_url(gruta.aurl(story)) + "\n\n" + tweet

            # truncate
            if len(tweet) > 240:
                tweet = tweet[0:239] + "\u2026"

            # does the story have an image?
            media_id = None

            if story.get("image") != "":
                # upload it
                img     = story.get("image").split("/")[-1]
                content = gruta.image(img)
                fn      = "/tmp/pygruta-twitter-media"

                if content is not None:
                    # write the content
                    f = open(fn, "wb")
                    f.write(content)
                    f.close()

                    f = open(fn, "rb")

                    try:
                        r = twitter.upload_media(media=f)
                        media_id = r["media_id"]
                    except:
                        gruta.log("ERROR", "Twitter-feed: UPLOAD failure")

                    try:
                        os.unlink(fn)
                    except:
                        pass

                else:
                    gruta.log("ERROR", "Twitter-feed: BAD image '%s'" % img)

            # some retries shortening the tweet
            r = 10
            while r > 0:
                try:
                    # tweet!
                    if media_id is not None:
                        twitter.update_status(status=tweet, media_ids=[media_id])
                    else:
                        twitter.update_status(status=tweet)

                    gruta.log("INFO", "Twitter-feed: POST %s" % gruta.url(story))

                    # mark this story as seen
                    follower.set("ldate", story.get("date"))
                    gruta.save_follower(follower)
                    r = 0

                except:
                    gruta.log("ERROR", "Twitter-feed: FAIL %s (len=%d)" % (
                        gruta.url(story), len(tweet)))

                    # shorten
                    tweet = tweet[0:-10] + "\u2026"

                    time.sleep(1)
                    r -= 1


            # wait a reasonable time between stories to avoid hammering the server
            t = 5 - (time.time() - t)

            if t > 0:
                time.sleep(t)
