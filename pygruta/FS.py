#
#   pygruta CMS
#   ttcdt <dev@triptico.com>
#
#   This software is released into the public domain.
#

#   Gruta source FS

import glob, os, hashlib, time, fcntl

from pygruta.base import Gruta

def open_ex(fn, mode="r"):
    """ Open exclusively a file. Returns None if cannot open """

    f = None

    while True:
        try:
            # open the file
            f = open(fn, mode)
        except:
            # can't open? return None
            break

        try:
            # non-blocking exclusive lock
            fcntl.flock(f, 6)
            # success; return file descriptor
            break

        except:
            # couldn't lock; close, wait and retry
            f.close()
            time.sleep(0.25)

    return f


class FS(Gruta):
    def __init__(self, path):
        self.path = path

        # init the base class
        super().__init__()

    def _flush(self):
        pass

    def _close(self):
        pass

    def id(self):
        return "FS (%s)" % self.path


    # helping functions

    def _file_to_dict(self, file):
        o = {}
    
        try:
            with open(file) as f:
                fcntl.flock(f, 1)

                for l in f:
                    l = l.rstrip().split(": ", 1)
                    if len(l) == 2:
                        l[0] = l[0].replace("-", "_")
                        l[1] = l[1].replace("\\n", "\n")
                        o[l[0]] = l[1]
        except:
            o = None
    
        return o
    
    def _file_to_string(self, file):
        try:
            return "".join(open(file))
        except:
            return ""
    
    def _dict_to_file(self, o, file, exclude=[]):
        with open(file, "w") as f:
            fcntl.flock(f, 2)

            for k, v in o.items():
                if k not in exclude:
                    if isinstance(v, list):
                        v = ",".join(v)

                    v = v.replace("\n", "\\n")

                    f.write("%s: %s\n" % (k, v))

    def _string_to_file(self, s, file):
        with open(file, "w") as f:
            f.write(s)



    # create

    def _create(self):
        # create main folder
        try:
            os.mkdir(self.path)
        except:
            pass

        # create subfolders
        for f in ("comments", "sids", "templates", "topics", "users",
                    "followers", "urls", "images"):
            try:
                os.mkdir(self.path + "/" + f)
            except:
                pass

        # touch the index
        index = self.path + "/topics/.INDEX"

        try:
            open(index)
        except:
            f = open(index, "w")
            f.close()


    # TOPICS

    def _load_topic(self, topic):
        file = "%s/topics/%s.M" % (self.path, topic.get("id"))

        return topic.fill(self._file_to_dict(file))

    def topics(self, private=False):
        for id in glob.glob("%s/topics/*.M" % (self.path)):
            id = os.path.basename(id).replace(".M", "")

            topic = self.topic(id)

            if private or topic.get("internal") != "1":
                yield(id)

    def _save_topic(self, topic):
        file = "%s/topics/%s" % (self.path, topic.get("id"))

        try:
            os.mkdir(file)
        except:
            pass

        self._dict_to_file(topic.data, file + ".M")

        return topic


    # STORIES

    def _load_story(self, story):
        if story.get("id") != "":
            file = "%s/topics/%s/%s" % (
                self.path, story.get("topic_id"), story.get("id")
            )

            # get metadata
            story = story.fill(self._file_to_dict(file + ".M"))

            if story is not None:
                story.set("content",  self._file_to_string(file))
                story.set("body",     self._file_to_string(file + ".B"))
                story.set("abstract", self._file_to_string(file + ".A"))
                story.set("hits",     self._file_to_string(file + ".H"))

                tags = story.get("tags").replace(", ", ",")
                if tags:
                    tags = tags.split(",")
                else:
                    tags = []

                story.set("tags", tags)
        else:
            story = None

        return story

    def _update_index(self, story, delete=False):
        index = "%s/topics/.INDEX" % self.path

        i = open_ex(index, "r")

        if i is not None:
            # new index
            ni = open(index + ".new", "w")

            t = story.get("topic_id")
            s = story.get("id")
            d = story.get("date")

            if delete is True:
                # null record entry
                r = None
            else:
                # record entry
                r = ":".join([
                    d,
                    t,
                    s,
                    ",".join(story.get("tags")),
                    story.get("udate")
                    ]) + "\n"

            # iterate current index
            for l in i:
                tr = l.replace("\n", "").split(":")

                # if not already saved and this record
                # is older, store here and destroy
                if r is not None and d > tr[0]:
                    ni.write(r)
                    r = None

                # store this record if it's not this story
                if t != tr[1] or s != tr[2]:
                    ni.write(l)

            # not yet stored? do it now
            if r is not None:
                ni.write(r)

            # now swap
            try:
                os.unlink(index + ".old")
            except:
                pass

            os.link(index,            index + ".old")
            os.rename(index + ".new", index)

            # finally close and release lock
            i.close()
            ni.close()

        else:
            # no index; create it
            l = []

            # loop al stories
            for t in self.topics():
                for s in self.stories(t):
                    story = self.story(t, s)

                    r = [
                        story.get("date") or ("0" * 14),
                        t,
                        s,
                        ",".join(story.get("tags")),
                        story.get("udate")
                    ]

                    l.append(":".join(r))

            # reverse order
            l.sort(reverse=True)

            with open(index, "w") as i:
                for r in l:
                    i.write(r + "\n")


    def _save_story(self, story):
        """ saves a story """
        file = "%s/topics/%s/%s" % (self.path, story.get("topic_id"), story.get("id"))

        self._dict_to_file(story.data, file + ".M", ["abstract", "body", "hits", "content"])
        self._string_to_file(story.get("content"),  file)
        self._string_to_file(story.get("body"),     file + ".B")
        self._string_to_file(story.get("abstract"), file + ".A")
        self._string_to_file(story.get("hits"),     file + ".H")

        self._update_index(story)

        return story


    def _delete_story(self, story):
        """ deletes a story """
        file = "%s/topics/%s/%s" % (self.path, story.get("topic_id"), story.get("id"))

        # de-index
        self._update_index(story, delete=True)

        # delete all files
        for ext in ["", ".M", ".B", ".A", ".H"]:
            try:
                os.unlink(file + ext)
            except:
                pass

        return None


    def stories(self, topic_id):
        if self.topic(topic_id) is None:
            raise KeyError("topic_id")

        for id in glob.glob("%s/topics/%s/*.M" % (self.path, topic_id)):
            id = os.path.basename(id).replace(".M", "")

            yield(id)


    # USERS

    def _load_user(self, user):
        file = "%s/users/%s" % (self.path, user.get("id"))

        return user.fill(self._file_to_dict(file))

    def _save_user(self, user):
        file = "%s/users/%s" % (self.path, user.get("id"))

        self._dict_to_file(user.data, file)

        return user

    def users(self, private=False):
        for id in glob.glob("%s/users/*" % (self.path)):
            id = os.path.basename(id)

            user  = self.user(id)
            xdate = user.get("xdate")

            if private is True or xdate == "" or xdate > self.today():
                yield(id)


    # FOLLOWERS

    def _load_follower(self, follower):
        file = "%s/followers/%s/%s" % (
            self.path, follower.get("user_id"), self.md5(follower.get("id")))

        return follower.fill(self._file_to_dict(file))

    def followers(self, user_id):
        for f in glob.glob("%s/followers/%s/*" % (self.path, user_id)):
            d = self._file_to_dict(f)

            yield d["id"]

    def _save_follower(self, follower):
        folder = "%s/followers/%s" % (self.path, follower.get("user_id"))

        try:
            os.mkdir(folder)
        except:
            pass

        file = folder + "/%s" % self.md5(follower.get("id"))

        self._dict_to_file(follower.data, file)

    def delete_follower(self, follower):
        file = "%s/followers/%s/%s" % (
            self.path, follower.get("user_id"), self.md5(follower.get("id")))

        try:
            os.unlink(file)
        except:
            pass


    # TEMPLATES

    def template(self, id):
        return self._file_to_string("%s/templates/%s" % (self.path, id))

    def save_template(self, id, content):
        return self._string_to_file(content, "%s/templates/%s" % (self.path, id))

    def templates(self):
        for id in glob.glob("%s/templates/*" % (self.path)):
            id = os.path.basename(id)

            yield id


    # IMAGES

    def image(self, id):
        content = None

        if self.valid_image_id(id):
            fn = "%s/images/%s" % (self.path, id)

            try:
                f = open(fn, "rb")
                content = f.read()
                f.close()
            except:
                pass

        return content

    def save_image(self, id, content):
        ok = False

        if self.valid_image_id(id):
            fn = "%s/images/%s" % (self.path, id)

            try:
                f = open(fn, "wb")
                f.write(content)
                f.close()
                ok = True
            except:
                pass

        return ok

    def images(self):
        for id in glob.glob("%s/images/*" % (self.path)):
            id = os.path.basename(id)

            yield id


    # SHORT URLS

    def unshorten_url(self, s_url):
        # get the last part
        if "/" in s_url:
            s_url = s_url.split("/")[-1]

        try:
            l_url = self._file_to_string("%s/urls/%s" % (self.path, s_url)).rstrip()
        except:
            l_url = ""

        return l_url

    def save_url(self, s_url, l_url):
        # create directory if needed
        try:
            os.mkdir("%s/urls" % self.path)
        except:
            pass

        # get the last part
        if "/" in s_url:
            s_url = s_url.split("/")[-1]

        self._string_to_file(l_url, "%s/urls/%s" % (self.path, s_url))

    def shorten_url(self, l_url):
        s_url, i = "", 1

        # iterate all directory
        for f in glob.glob("%s/urls/*" % (self.path)):
            s = self._file_to_string(f).rstrip()

            if s == l_url:
                # found!
                s_url = os.path.basename(f)
                break
            else:
                i += 1

        # not found? create new
        if s_url == "":
            s_url = "%x" % i
            self.save_url(s_url, l_url)

        return self.aurl("/s/%s" % s_url)

    def urls(self):
        for u in glob.glob("%s/urls/*" % self.path):
            yield self.aurl("/s/%s" % os.path.basename(u))


    # STORY SETS

    def story_set(self, topics=None, tags=None, content=None, order="date",
                  d_from=None, d_to=None, num=None, offset=0, private=False,
                  timeout=None):
        res = 0
        cnt = 0

        today = self.today()

        if order == "hits":
            index_file = self.path + "/topics/.top_ten"
        else:
            index_file = self.path + "/topics/.INDEX"

        if timeout is not None:
            timeout += time.time()

        with open(index_file) as I:
            fcntl.flock(I, 1)

            for l in I:
                # timeout?
                if timeout is not None and time.time() > timeout:
                    break

                l = l.rstrip().split(":")

                # ensure 5 elements
                while len(l) < 5:
                    l.append("")

                # pick data
                (s_date, s_topic, s_id, s_stags, s_udate) = l

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

                # matching tags?
                if s_stags != "":
                    s_tags = s_stags.replace(", ", ",").split(",")
                else:
                    s_tags = []

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
                yield (s_topic, s_id, s_date, s_tags, s_udate)

                res += 1

                # finish if we have all the stories we need
                if num is not None and res == num:
                    break

