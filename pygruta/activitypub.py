#
#   pygruta CMS
#   ttcdt <dev@triptico.com>
#
#   This software is released into the public domain.
#

#   ActivityPub support

import time, json, re
import OpenSSL
import base64
import datetime
import hashlib

import pygruta
import pygruta.html
import pygruta.http

# functions

def query_webfinger(id):
    """ Queries webfinger about this id """
    status = 404
    body = None
    query = ""
    resource = ""

    if re.search("^@?[^@]+@[^@]+$", id):
        # @user@host
        query = "https://" + re.sub("^@?[^@]+@", "", id)

        resource = "acct:" + re.sub("^@", "", id)

    elif re.search("^https?://", id):
        # url
        x = re.search("^https?://[^/]+", id)
        query = x.group(0)
        resource = id

    if query:
        query += "/.well-known/webfinger?resource=" + resource

        # do the query
        status, body = pygruta.http.request("GET", query, headers={
            "Accept": "application/json"}
        )

    return status, body


def get_user(gruta, uid):
    """ gets a user and ensures it has valid RSA keys """

    user = gruta.user(uid)

    if user is not None and user.get("privkey") == "":
        # do the magic to create the keys

        pk = OpenSSL.crypto.PKey()
        pk.generate_key(OpenSSL.crypto.TYPE_RSA, 4096)

        pem = OpenSSL.crypto.dump_privatekey(
            OpenSSL.crypto.FILETYPE_PEM, pk)

        user.set("privkey", pem.decode("ascii"))

        pem = OpenSSL.crypto.dump_publickey(
            OpenSSL.crypto.FILETYPE_PEM, pk)

        user.set("pubkey", pem.decode("ascii"))

        gruta.save_user(user)

    return user


def get_actor(actor_url):
    """ gets an actor object """

    status, actor = pygruta.http.request("GET", actor_url, headers={
        "Accept": "application/activity+json" }
    )

    if status == 200:
        try:
            actor = json.loads(actor)
        except:
            actor = None

    return status, actor



def send_to_inbox(gruta, user, inbox, msg):
    """ sends an ActivityPub JSON object to an inbox """

#    print("send to inbox")

    body = json.dumps(msg)

    # calculate signature parts
    s = re.sub("^https://", "", inbox)
    host, target = s.split("/", 1)

    target = "post /" + target

    date = datetime.datetime.utcnow().strftime("%a, %d %b %Y %H:%M:%S GMT")

    # digest
    m = hashlib.sha256()
    m.update(body.encode())
    digest = "SHA-256=" + base64.b64encode(m.digest()).decode()

    # string to be signed
    s  = "(request-target): " + target + "\n"
    s += "host: " + host + "\n"
    s += "digest: " + digest + "\n"
    s += "date: " + date

    gruta.log("DEBUG", "ActivityPub: string to be signed '%s'" % s)

    # build a key object
    pk = OpenSSL.crypto.load_privatekey(
        OpenSSL.crypto.FILETYPE_PEM, user.get("privkey"))

    b = OpenSSL.crypto.sign(pk, s, "sha256")
    sig_b64 = base64.b64encode(b).decode()

    # build the signature header
    key_name = gruta.aurl(user.get("id"), "activitypub/user") + "#main-key"

    signature = "keyId=\"" + key_name + "\","
    signature += "algorithm=\"rsa-sha256\","
    signature += "headers=\"(request-target) host digest date\","
    signature += "signature=\"" + sig_b64 + "\""

    gruta.log("DEBUG", "ActivityPub: signature '%s'" % signature)

    # send the POST
    status, data = pygruta.http.request("POST", inbox, headers={
        "Content-Type":     "application/activity+json",
        "Date":             date,
        "Signature":        signature,
        "Digest":           digest
        }, body=body)

    try:
        reply = data.decode()
    except:
        reply = str(data)

    if status < 200 or status > 299:
        gruta.log("ERROR", "ActivityPub: %s SENDING TO '%s' (%d, '%s')" % (
            user.get("id"), inbox, status, reply))

    else:
        gruta.log("DEBUG", "ActivityPub: %s SENT '%s' (%d, '%s')" % (
            user.get("id"), inbox, status, reply))

    return status, data


def send_to_actor(gruta, user, actor_url, msg):
    """ sends an ActivityPub JSON object to an actor """

    status, actor_o = get_actor(actor_url)

    if status < 400 and actor_o is not None:
        status, data = send_to_inbox(gruta, user, actor_o["inbox"], msg)
    else:
        data = None

    return status, data


def note(gruta, user, message, dest=None, url=None, subject="",
         date=None, attachment=[]):
    """ Creates a Note object """

    if date is None:
        date = gruta.today_utc()

    if dest is None:
        dest = "https://www.w3.org/ns/activitystreams#Public"

    if url is None:
        url = gruta.aurl("%f" % time.time())

    n_attachment = []

    # build the attachment list
    for a in attachment:
        mediaType = gruta.image_mime_type(a)

        if mediaType:
            n_attachment.append({
                "mediaType": mediaType,
                "url":       a,
                "name":      None,
                "type":      "Document"
            })

    # build the date
    n_date = date[0:4] + "-" + date[4:6] + "-" + date[6:8]
    n_date += "T" + date[8:10] + ":" + date[10:12] + ":" + date[12:14] + "Z"

    uid = user.get("id")

    n = {
        "id":               url + "#pygruta-note-" + uid,
        "type":             "Note",
        "to":               [dest],
        "summary":          subject,
        "content":          message,
        "url":              url,
        "atomUri":          url + "#pygruta-note-" + uid,
        "attributedTo":     gruta.aurl(uid, "activitypub/user"),
        "published":        n_date,
        "cc":               [],
        "sensitive":        False,
        "inReplyToAtomUri": None,
        "inReplyTo":        None,
        "attachment":       n_attachment
    }

    return n


def note_from_story(gruta, story):
    """ Builds an ActivityPub Note object from a story """

    # story url
    url = gruta.aurl(story)

    # build the date
    date = story.get("date")
    date = date[0:4] + "-" + date[4:6] + "-" + date[6:8] + "T" + date[8:10] + ":" + date[10:12] + ":" + date[12:14] + "Z"

    # build the content doing some acrobatics
    # (this is mostly for Mastodon; others will probably differ)
    content = "<p><a href=\"" + url + "\">" + url + "</a></p>"
    content += pygruta.special_uris(gruta, story.get("abstract"), absolute=True)
    content = content.replace("</p>\n", "")
    content = content.replace("<p>\n", "<p>")
    content = content.replace("\n<p>", "<p>")
    content = content.replace("<li>", "<li>&bull; ")

    # build the src
    src = gruta.aurl(story.get("userid"), "activitypub/user")

    # build the attachment
    attachment = []

    image = story.get("image")

    if re.search(r"\.jpe?g$", image):
        attachment.append({
            "mediaType": "image/jpeg",
            "url":       gruta.aurl(image),
            "name":      None,
            "type":      "Document"
            })

    if re.search(r"\.gif$", image):
        attachment.append({
            "mediaType": "image/gif",
            "url":       gruta.aurl(image),
            "name":      None,
            "type":      "Document"
            })

    if re.search(r"\.png$", image):
        attachment.append({
            "mediaType": "image/png",
            "url":       gruta.aurl(image),
            "name":      None,
            "type":      "Document"
            })

    # find hashtags
    tags = []
    for t in re.findall("#[0-9A-Za-z\xc0-\xff]+", content):
        tags.append({
            "type": "Hashtag",
            "href": gruta.aurl("/tag/%s.html" % t[1:]),
            "name": t
        })

    # the reference field can contain an URL
    in_reply_to = story.get("reference")

    if in_reply_to == "":
        in_reply_to = None

    uid = story.get("userid")

    n = {
        "id":               url + "#pygruta-note-" + uid,
        "atomUri":          url + "#pygruta-note-" + uid,
        "type":             "Note",
        "to":               ["https://www.w3.org/ns/activitystreams#Public"],
        "summary":          story.get("title"),
        "content":          content,
        "url":              url,
        "attributedTo":     src,
        "published":        date,
        "cc":               [],
        "sensitive":        False,
        "inReplyToAtomUri": in_reply_to,
        "inReplyTo":        in_reply_to,
        "attachment":       attachment,
        "tag":              tags
    }

    return n


def send_note_to_actor(gruta, user, dest, note):
    """ Sends a Note (wrapping it in a Create object) and sends to dest """

    # create object, date now
    date = datetime.datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")

    # build the src
    src = gruta.aurl(user.get("id"), "activitypub/user")

    # create the "Create" object
    c = {
        "type":         "Create",
        "to":           [dest],
        "cc":           [],
        "actor":        src,
        "object":       note,
        "id":           note["url"] + "#pygruta-create",
        "published":    date,
        "@context": [
            "https://www.w3.org/ns/activitystreams"
        ]
    }

    return send_to_actor(gruta, user, dest, c)



def react(gruta, user, url, type="Like"):
    """ Sends a reaction to a url """

    body = None

    # get the url to get its actor
    status, object = pygruta.http.request("GET", url, headers={
        "Accept": "application/activity+json" }
    )

    try:
        object = json.loads(object)
    except:
        object = None

    if object is not None:
        # get actor
        try:
            actor = object["attributedTo"]
        except:
            actor = None

        if actor is not None:
            # build a reaction object
            me = gruta.aurl(user.get("id"), "activitypub/user")

            reaction = {
                "@context": "https://www.w3.org/ns/activitystreams",
                "object":   object,
                "actor":    me,
                "id":       me + "/react/%s/%d" % (type, time.time()),
                "type":     type
            }

            status, body = send_to_actor(gruta, user, actor, reaction)

        else:
            gruta.log("ERROR", "ActivityPub: %s CANNOT GET ACTOR '%s'" % (
                user.get("id"), object))

    else:
        gruta.log("ERROR", "ActivityPub: %s BAD OBJECT (%d)" % (user.get("id"), status))

    return status, body


def send_feed(gruta):
    """ Sends a blog feed to all followers """

    for s in reversed(list(gruta.feed())):

        # get start time for this story
        t = time.time()

        story = gruta.story(s[0], s[1])

        # build a note
        note = note_from_story(gruta, story)

        cnt = 0

        # get story author
        uid = story.get("userid")
        user = get_user(gruta, uid)

        # iterate the followers of this user
        for fid in gruta.followers(uid):

            follower = gruta.follower(uid, fid)

            if follower.get("network") == "activitypub" and follower.get("disabled") != "1":

                # had this follower seen only older stories?
                if follower.get("ldate") < story.get("date"):
                    status, body = send_note_to_actor(gruta, user, fid, note)

                    if status >= 200 and status <= 299:
                        # follower received the story
                        failures = 0
                        follower.set("ldate", story.get("date"))
                    else:
                        # account one more failure
                        failures = int(follower.get("failures") or "0") + 1

                        try:
                            body = body.decode()
                        except:
                            body = str(body)

                        gruta.log("ERROR",
                            "ActivityPub-feed: %s POST ERROR '%s': %d, '%s'" % (
                                uid, fid, status, body))

                    # update failure count
                    follower.set("failures", str(failures))

                    gruta.log("INFO",
                        "ActivityPub-feed: %s POST '%s' story: %s, sts: %s, fail#: %d" % (
                        uid, fid, gruta.url(story), status, failures))

                    # too many failures? disable follower
                    if failures > 25:
                        # disable user
                        follower.set("disabled", "1")

                        gruta.log("INFO",
                            "ActivityPub-feed: %s DISABLED '%s' (too many failures)" % (
                                uid, fid))

                    # save changes in follower
                    gruta.save_follower(follower)

                    # count one more post
                    cnt += 1

        # any posts for this story?
        if cnt > 0:
            # wait a reasonable time between stories to avoid hammering servers
            t = 5 - (time.time() - t)

            if t > 0:
                time.sleep(t)


# httpd handlers

def webfinger_get_handler(gruta, q_path, q_vars):
    """ webfinger GET handler """

    status, body = 0, None

    if q_path == "/.well-known/webfinger":
        try:
            # resource is acct:user@hostname
            res = q_vars["resource"][0]
            q_user, q_host = res.replace("acct:", "").split("@")

            if q_host == gruta.host_name:
                # host matches; find user
                user = get_user(gruta, q_user)

                if user is not None:
                    # user exists: create object
                    body = {
                        "subject": res,
                        "links": [
                            {
                                "rel": "self",
                                "type": "application/activity+json",
                                "href": gruta.aurl(q_user, "activitypub/user")
                            }
                        ]
                    }

                    body = json.dumps(body)
                    status = 200
        except:
            pass

    return status, body, "application/json"


def get_handler(gruta, q_path, q_vars):
    """ ActivityPub GET handler """

    status, body = 0, None

    if re.search("^/activitypub/user/.+", q_path):

        uid = q_path.split("/")[-1]
        user = get_user(gruta, uid)

        if user is not None:
            actor  = gruta.aurl(uid, "activitypub/user")
            inbox  = gruta.aurl(uid, "activitypub/inbox")
            outbox = gruta.aurl(uid, "activitypub/outbox")
    
            body = {
                "@context": [
                    "https://www.w3.org/ns/activitystreams",
                    "https://w3id.org/security/v1"
                    ],
                "id": actor,
                "url": user.get("url"),
                "type": "Person",
                "preferredUsername": uid,
                "name": user.get("username"),
                "inbox": inbox,
                "outbox": outbox,
                "followers": gruta.aurl(uid, "activitypub/followers"),
                "following": gruta.aurl(uid, "activitypub/following"),
                "liked": gruta.aurl(uid, "activitypub/liked"),
                "summary": user.get("bio"),
                "icon": {
                    "mediaType": "image/jpeg",
                    "type": "Image",
                    "url": user.get("avatar")
                },
                "publicKey": {
                    "id": actor + "#main-key",
                    "owner": actor,
                    "publicKeyPem": user.get("pubkey")
                }
            }
    
            status, body = 200, json.dumps(body)

        else:
            status = 404

    elif re.search("^/activitypub/outbox/.+", q_path):
        status, body = 200, ""


    return status, body, "application/activity+json"


def inbox_post_handler(gruta, q_path, q_vars, p_data):
    """ ActivityPub inbox POST handler """

    status, body = 404, None

    uid = q_path.split("/")[-1]
    user = get_user(gruta, uid)

    dump_data = False

    if user is not None:
        j = json.loads(p_data)

        actor = gruta.aurl(uid, "activitypub/user")

        if j["type"] == "Follow":
            # Build an Accept request
            # to acknowledge the following
            o = {
                "type": "Accept",
                "id": "%s/%f" % (actor, time.time()),
                "object": j,
                "actor": actor,
                "@context": [
                    "https://www.w3.org/ns/activitystreams",
                    "https://w3id.org/security/v1"
                ]
            }

            gruta.log("INFO", "ActivityPub: %s FOLLOW REQUEST '%s'" % (
                uid, j["actor"]));

            status, data = send_to_actor(gruta, user, j["actor"], o)

#            print("STATUS:", status, "DATA:", data)

            if status >= 200 and status <= 299:

                # store as a follower: new posts
                # will be sent to these people

                follower = gruta.new_follower({
                    "id":       j["actor"],
                    "user_id":  uid,
                    "date":     gruta.today(),
                    "context":  p_data,
                    "network":  "activitypub"
                    })

                gruta.save_follower(follower)
                gruta.notify("ActivityPub: %s NEW FOLLOWER '%s'" % (
                    uid, j["actor"]))

                # created
                status = 201

            else:
                try:
                    data = data.decode()
                except:
                    data = str(data)

                gruta.log("ERROR", "ActivityPub: %s FOLLOW CONFIRM '%s' failed: '%s'" % (
                    uid, j["actor"], data))

        elif j["type"] == "Undo":
            o = j["object"]
            gruta.log("INFO", "ActivityPub: UNDO object type '%s'" % o["type"])

            if o["type"] == "Follow":
                # delete from followers
                try:
                    follower = gruta.follower(user.get("id"), j["actor"])
    
                    if follower:
                        gruta.delete_follower(follower)
                        gruta.notify("ActivityPub: %s UNFOLLOW '%s'" % (uid, j["actor"]))
    
                        status = 200
                    else:
                        gruta.log("ERROR", "ActivityPub: %s BAD UNFOLLOW '%s'" % (
                            uid, j["actor"]))

                        status = 403

                except:
                    status = 402
            else:
                gruta.log("WARN", "ActivityPub: %s Unhandled undo for type '%s'" % (
                    uid, o["type"]))

                dump_data = True

        elif j["type"] == "Create" or j["type"] == "Update":
            o = j["object"]
            gruta.log("INFO", "ActivityPub: %s CREATE object type '%s'" % (uid, o["type"]))

            if o["type"] == "Note" or o["type"] == "Article":
                # It's a Note: store as a story

                # ensure the topic 'activitypubs' exists
                if gruta.topic("activitypubs") is None:
                    topic = gruta.new_topic({
                        "id":       "activitypubs",
                        "name":     "ActivityPub posts",
                        "internal": "1"
                        }
                    )
                    gruta.save_topic(topic)

                # build an id by hashing the full message
                id = gruta.md5(p_data)

                # get message data
                actor     = j["actor"]
                text      = o["content"]
                redir     = o["id"]
                context   = p_data

                status, actor_o = get_actor(actor)

                if actor_o:
                    actor_username = actor_o["preferredUsername"]
                else:
                    actor_username = actor

                if o.get("name"):
                    title = o["name"]
                elif o.get("summary"):
                    title = o["summary"]
                else:
                    title = "Message from " + actor_username

                story = gruta.story("activitypubs", id)

                if story is None:
                    story = gruta.new_story({
                        "topic_id": "activitypubs",
                        "id":       id
                    })

                content = "<h2>" + title + "</h2>\n"
                content += "<p><a href =\"" + redir + "\">Message</a>"
                content += " from <a href=\"" + actor + "\">" + actor_username + "</a>"
                content += " to " + uid + ":</p>\n"
                content += "<blockquote>\n" + text + "</blockquote>\n"
                content += "<p></p>\n"

                # does the message include attachments?
                l = o.get("attachment")

                if isinstance(l, list) and len(l) > 0:
                    a = l[0]

                    # an image: add an img tag
                    if a["mediaType"] in ["image/jpeg", "image/gif", "image/png"]:
                        content += "<p><img src=\"" + a["url"] + "\"/></p>"
                        content += "<p></p>\n"

                story.set("title",      title)
                story.set("redir",      redir)
                story.set("context",    context)
                story.set("content",    content)
                story.set("full_story", "1")

                gruta.save_story(story)

                gruta.notify("ActivityPub: %s NEW MESSAGE '%s'" % (uid, redir))

                status = 201

        elif j["type"] == "Like" or j["type"] == "Announce":
            # build an id by hashing the full message
            new_id = gruta.md5(p_data)

            # get info about the actor
            status, actor_o = get_actor(j["actor"])

            # get the story that is being liked
            object = j["object"]
            object = re.sub("^" + gruta.aurl(), "", object)
            object = re.sub("\.html.*$", "", object)

            try:
                topic_id, id = object.split("/")
                story = gruta.story(topic_id, id)
            except:
                story = None

            if j["type"] == "Like":
                symbol = "&#9733;"
                verb   = "liked"
            else:
                symbol = "&#8634;"
                verb   = "boosted"

            if story is not None:
                content = "<h2>" + symbol + " " + story.get("title") + "</h2>\n"
                content += "<p><a href=\"" + j["actor"] + "\">"
                content += actor_o["preferredUsername"] + "</a>"
                content += " " + verb + " story://%s/%s</p>" % (topic_id, id)

                # get the local page, stripping the #pygruta-stuff
                reference = re.sub("#.*$", "", j["object"])

                new_story = gruta.new_story({
                    "id":           new_id,
                    "topic_id":     "activitypubs",
                    "content":      content,
                    "full_story":   "1",
                    "context":      p_data,
                    "reference":    reference
                })

                gruta.save_story(new_story)

                gruta.notify("ActivityPub: %s REACTION from '%s' to '%s'" % (
                    uid, j["actor"], j["object"]))

                status = 200
            else:
                gruta.log("ERROR",
                    "ActivityPub: %s REACTION invalid for '%s'" % (uid, j["object"]))

        elif j["type"] == "Delete":
            # is this actor following us?
            follower = gruta.follower(user.get("id"), j["actor"])

            if follower is not None:
                gruta.delete_follower(follower)
                gruta.notify("ActivityPub: %s DELETED '%s'" % (uid, j["actor"]))

            else:
                # ignore Delete queries
                gruta.log("INFO", "ActivityPub: %s DELETE ignored for '%s'" % (
                    uid, j["actor"]))

            status = 200

        else:
            gruta.log("WARN", "ActivityPub: %s Unhandled type '%s'" % (uid, j["type"]))
            dump_data = True

    if dump_data is True:
        gruta.log("DEBUG", "ActivityPub: %s p_data: %s" % (uid, p_data))

    return status, body, "application/activity+json"
