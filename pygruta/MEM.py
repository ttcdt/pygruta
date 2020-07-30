#
#   pygruta CMS
#   ttcdt <dev@triptico.com>
#
#   This software is released into the public domain.
#

#   Gruta source MEM

import json, time, base64
from pygruta.base import Gruta

class MEM(Gruta):
    def __init__(self, file):
        self.file = file

        # load the file
        try:
            self.db = json.loads("".join(open(self.file)))
        except:
            self.db = { ".INDEX": [] }

        # ensure all keys exist
        for k in ("topics", "stories", "users", "followers",
                  "templates", "images", "comments"):
            if self.db.get(k) is None:
                self.db[k] = {}

        # number of pending modifications
        self.mod = 0

        # init the base class
        super().__init__()

    def id(self):
        return "MEM (%s)" % self.file


    def _save(self):
        """ save the db to JSON if there are pending modifications """
        if self.mod > 0:
            with open(self.file, "w") as f:
                f.write(json.dumps(self.db))

            self.mod = 0

    def _flush(self):
        self._save()

    def _close(self):
        self._save()

    def _create(self):
        pass


    # TOPICS

    def _load_topic(self, topic):
        topic.data = self.db["topics"].get(topic.get("id"))
        return topic if topic.data is not None else None

    def _save_topic(self, topic):
        id = topic.get("id")
        self.db["topics"][id] = topic.data

        if self.db["stories"].get(id) is None:
            self.db["stories"][id] = {}

        self.mod += 1

        return topic

    def topics(self, private=False):
        for id in self.db["topics"]:
            topic = self.topic(id)

            if private or topic.get("internal") != "1":
                yield id


    # STORIES

    def _load_story(self, story):
        topic_id = story.get("topic_id")
        id       = story.get("id")

        if self.db["stories"].get(topic_id) is not None:
            story.data = self.db["stories"][topic_id].get(id)

            if story.data is None:
                story = None
        else:
            story = None

        return story

    def _save_story(self, story):
        topic_id = story.get("topic_id")
        id       = story.get("id")

        if self.db["stories"].get(topic_id) is not None:
            self.db["stories"][topic_id][id] = story.data

            self._update_index(story)
        else:
            story = None

        self.mod += 1

        return story

    def _update_index(self, story, delete=False):
        I = []

        t = story.get("topic_id")
        s = story.get("id")
        d = story.get("date")

        if delete is True:
            # null record entry
            r = None
        else:
            # record entry
            r = [ d, t, s, story.get("tags"), story.get("udate") ]

        for i in self.db[".INDEX"]:
            # if not already saved and this record
            # is older, store here and destroy
            if r is not None and d > i[0]:
                I.append(r)
                r = None

            # store this record if it's not this story
            if t != i[1] or s != i[2]:
                I.append(i)

        # not yet stored? do it now
        if r is not None:
            I.append(r)

        self.db[".INDEX"] = I

    def _delete_story(self, story):
        k = story.get("topic_id") + "/" + story.get("id")
        del self.db["stories"][k]

        self._update_index(story, delete=True)

        self.mod += 1

        return None

    def stories(self, topic_id):
        if self.db["stories"].get(topic_id):
            for id in self.db["stories"][topic_id]:
                yield id


    # USERS

    def _load_user(self, user):
        user.data = self.db["users"].get(user.get("id"))
        return user if user.data is not None else None

    def _save_user(self, user):
        id = user.get("id")

        self.db["users"][id] = user.data

        if self.db["followers"].get(id) is None:
            self.db["followers"][id] = {}

        self.mod += 1

        return user

    def users(self, private=False):
        for id in self.db["users"]:

            user  = self.user(id)
            xdate = user.get("xdate")

            if private is True or xdate == "" or xdate > self.today():
                yield id



    # FOLLOWERS

    def _load_follower(self, follower):
        uid = follower.get("user_id")
        id  = follower.get("id")

        if self.db["followers"].get(uid) is not None:
            follower.data = self.db["followers"][uid].get(id)

            if follower.data is None:
                follower = None
        else:
            follower = None

        return follower

    def _save_follower(self, follower):
        uid = follower.get("user_id")
        id  = follower.get("id")

        if self.db["followers"].get(uid) is not None:
            self.db["followers"][uid][id] = follower.data
        else:
            follower = None

        self.mod += 1

        return follower

    def delete_follower(self, follower):
        uid = follower.get("user_id")
        id  = follower.get("id")

        if self.db["followers"].get(uid) is not None:
            del self.db["followers"][uid][id]

        return None

    def followers(self, user_id):
        if self.db["followers"].get(user_id) is not None:
            for id in self.db["followers"][user_id]:
                yield id



    # TEMPLATES

    def template(self, id):
        return self.db["templates"].get(id) or ""

    def save_template(self, id, content):
        self.db["templates"][id] = content
        self.mod += 1

    def templates(self):
        for id in self.db["templates"]:
            yield id


    # IMAGES

    def image(self, id):
        try:
            content = self.db["images"][id]

            # convert from base64 to binary
            content = base64.b64decode(content)
        except:
            content = None

        return content

    def save_image(self, id, content):
        ok = False

        if self.valid_image_id(id):
            # convert to base64
            content = base64.b64encode(content).decode()

            self.db["images"][id] = content
            self.mod += 1

            ok = True

        return ok

    def images(self):
        for id in self.db["images"]:
            yield id


    # STORY SETS

    def story_set(self, topics=None, tags=None, content=None, order="date",
                  d_from=None, d_to=None, num=None, offset=0, private=False,
                  timeout=None):
        res = 0
        cnt = 0

        today = self.today()

        if timeout is not None:
            timeout += time.time()

        for i in self.db[".INDEX"]:
            # timeout?
            if timeout is not None and time.time() > timeout:
                break

            # pick data
            s_date, s_topic, s_id, s_tags, s_udate = i

            # not on topic?
            if topics is not None:
                if not s_topic in topics:
                    continue

            # skip if date is above the threshold
            if d_to is not None and s_date > d_to:
                continue

            # exit if date is below the threshold
            if d_from is not None and s_date < d_from:
                break

            # were private stories not requested?
            if not private:
                # reject still unpublished stories
                if s_date > today:
                    continue

                # reject un-published stories
                if s_udate != "" and s_udate < today:
                    continue

                # reject stories from internal topics
                t = self.topic(s_topic)

                if t is None or t.get("internal") == "1":
                        continue

            if tags is not None:
                if not self.is_subset_of(tags, s_tags):
                    continue

            # matching content?
            if content is not None:
                s = self.story(id=s_id, topic_id=s_topic)

                if content.lower() not in s.get("content").lower():
                    continue

            # this story matches the desired set
            cnt += 1

            if cnt <= offset:
                continue

            # result!
            yield s_topic, s_id, s_date, s_tags, s_udate

            res += 1

            # finish if we have all the stories we need
            if num is not None and res == num:
                break
