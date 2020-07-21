#
#   pygruta CMS
#   ttcdt <dev@triptico.com>
#
#   This software is released into the public domain.
#

#   Webmention support

import re, urllib, time

import pygruta
import pygruta.html
import pygruta.http

def post_handler(gruta, p_data):
    """ POST handler """

    # default: bad request
    status = 400

    if p_data.get("source") and p_data.get("target"):
        source = p_data["source"][0]
        target = p_data["target"][0]

        # ensure a 'webmentions' topic exists
        if gruta.topic("webmentions") is None:

            topic = gruta.new_topic({
                "id":       "webmentions",
                "internal": "1",
                "name":     "Webmention posts"
                })

            gruta.save_topic(topic)

        # target must match this
        # source must *not* match this
        match = gruta.template("cfg_webmention_regex")

        if match == "":
            match = "^https?://(www\.)?%s" % gruta.host_name

        if not re.search(match, source) and re.search(match, target):
            # target is on this host and source does not

            # build a unique id based of source and target
            id = gruta.md5(source + ":" + target)

            # get the story
            story = gruta.story("webmentions", id)

            # download the source
            status, body = pygruta.http.request("GET", source)

            if status == 200:
                # source is here: iterate the links

                body = body.decode("utf-8")

                found = False
                for l in pygruta.html.links_in_content(body):
                    if l[2] == target:
                        found = True
                        break

                if found:
                    # it's true: source links to target

                    # find a title
                    x = re.search("<\s*title[^>]*>([^<]+)<\s*/title",
                            body, flags=re.IGNORECASE)
                    if x:
                        title = x.group(1)
                    else:
                        title = "Webmention from " + source

                else:
                    # no (or no longer)
                    # "precondition failed"
                    gruta.log("ERROR",
                        "Webmention: target='%s' not linked from source='%s'" % (
                        target, source))

                    status = 412
            else:
                gruta.log("ERROR", "Webmention: cannot fetch source '%s'" % source)

            if status < 400:
                # if story does not exist, create it
                if story is None:
                    story = gruta.new_story({
                        "id":       id,
                        "topic_id": "webmentions"
                        })

                    # infer the mention type
                    if re.search("class\s*=\s*['\"]u-repost-of", body):
                        type = "repost"

                    elif re.search("class\s*=\s*['\"]u-like-of", body):
                        type = "like"

                    elif re.search("class\s*=\s*['\"]u-follow-of", body):
                        type = "follow"

                    else:
                        type = "link"

                    # convert them to 'clickable'
                    source_l = re.sub("^https://", "links://", source)
                    target_l = re.sub("^https://", "links://", target)

                    new_content = "<h2>" + title + "</h2>\n"
                    new_content += "<dl>\n"
                    new_content += "<dt><b>source:</b></dt><dd>" + source_l + "</dd>\n"
                    new_content += "<dt><b>target:</b></dt><dd>" + target_l + "</dd>\n"
                    new_content += "<dt><b>type:</b></dt><dd>" + type + "</dd>\n"
                    new_content += "</dl>\n"

                    story.set("title",       title)
                    story.set("content",     new_content)
                    story.set("full_story",  "1")
                    story.set("redir",       source)
                    story.set("reference",   target)
                    story.set("description", "Webmention for " + target)

                    gruta.save_story(story)

                    gruta.notify("New Webmention: " + source)

                    # new webmention, notify as "Created"
                    status = 201

            else:
                # story must be deleted
                # ...
                pass

        else:
            # bad request
            gruta.log("ERROR", "Webmention: mismatch source='%s' target='%s'" % (source, target))

    else:
        gruta.log("ERROR", "Webmention: source or target not defined")

    return status, "", None


def send_feed(gruta):
    """ Sends Webmentions to links in a blog feed """

    match = gruta.template("cfg_webmention_regex")

    if match == "":
        match = "^https?://(www\.)?%s" % gruta.host_name

    for s in gruta.feed():
        # get story
        story = gruta.story(s[0], s[1])

        source = gruta.aurl(story)

        # test if modification time is more than a week old
        dt = time.time() - int(gruta.date_format(story.get("mtime"), "%s"))

        if dt > 7 * 24 * 60 * 60:
            gruta.log("INFO", "Webmention-feed: skipping untouched story '%s' (%ds)" % (
                source, dt))

            continue

        content = pygruta.special_uris(gruta, story.get("body"), absolute=True)

        # iterate all links in story
        for lc in pygruta.html.links_in_content(content):
            target = lc[2]

            # is it an external link?
            if not re.search(match, target) and re.search("^https?://", target):

                status, body = pygruta.http.request("GET", target)

                if status == 200:

                    hook = ""
                    for l in pygruta.html.links_in_content(body):
                        le = l[0]

                        if le.tag == "link" and le.attrib.get("rel") == "webmention":
                            hook = le.attrib.get("href")
                            break

                    if hook.startswith("https://"):
                        body = urllib.parse.urlencode({
                            "source": source,
                            "target": target
                        })

                        status, body = pygruta.http.request("POST", hook, body=body)

                        gruta.log("INFO",
                            "Webmention-feed: [1] %d, src: %s, trgt: %s, hook: %s" % (
                                status, source, target, hook))

                        if status < 200 or status > 299:
                            # retry differently
                            status, body = pygruta.http.request("POST", hook, fields={
                                "source": source, "target": target})

                            gruta.log("INFO",
                                "Webmention-feed: [2] %d, src: %s, trgt: %s, hook: %s" % (
                                    status, source, target, hook))

                else:
                    gruta.log("ERROR", "Webmention-feed: cannot fetch trgt '%s'" % target)
