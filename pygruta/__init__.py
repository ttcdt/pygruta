#
#   pygruta CMS
#   ttcdt <dev@triptico.com>
#
#   This software is released into the public domain.
#

import time, re

__version__ = "1.42"

def log_str(category, string):
    return "%-5s: %s %s" % (category, time.strftime("%Y-%m-%d %H:%M:%S"), string)

def log(category, string):
    print(log_str(category, string), flush=True)


def open(source):
    """ opens a source driver """

    if re.search("\.json$", source):
        # it's a JSON-backed DB: return MEM
        import pygruta.MEM
        return pygruta.MEM.MEM(source)

    elif source[0] == "/":
        # it's a path; return FS
        import pygruta.FS
        return pygruta.FS.FS(source)

    return None


def special_uris(gruta, s, e=0, absolute=False):
    """ Processes the special URIs """

    regexes = [
        r'(story)://([\w0-9_-]+)/([\w0-9_-]+)\s*\(([^\)]+)\)',
        r'(story)://([\w0-9_-]+)/([\w0-9_-]+)',
        r'(topic)://([\w0-9_-]+)',
        r'(links?)://([^\s<]+)\s*\(([^\)]+)\)',
        r'(links?)://([^\s<]+)',
        r'(img)://([\w0-9_\.-]+)/([\w0-9_-]+)',
        r'(img)://([\w0-9_\.-]+)',
        r'(thumb)://([\w0-9_\.-]+)/([\w0-9_-]+)',
        r'(thumb)://([\w0-9_\.-]+)',
        r'(body)://([\w0-9_-]+)/([\w0-9_-]+)',
        r"(h-card)://([\w0-9_-]+)",
        r"(user)://([\w0-9_-]+)",
        r'(tag)://([^\s<]+)?\s*\(([^\)]+)\)',
        r'(tag)://([^\s<]+)?'
    ]

    if e >= len(regexes):
        # out of the list of regexes: return string as is
        ret = s

    else:
        # try this regex
        x = re.search(regexes[e], s)

        if x is None:
            # not matched; try next
            ret = special_uris(gruta, s, e + 1, absolute)

        else:
            # split string by the match
            pre, post = s.split(x.group(0), maxsplit=1)

            # convert first part
            ret = special_uris(gruta, pre, e + 1, absolute)

            uri = x.group(1)


            if uri == "story":

                story = gruta.story(x.group(2), x.group(3))

                if story:
                    try:
                        title = x.group(4)
                    except:
                        title = story.get("title")

                    ret += "<a href=\"" + gruta.url(story, absolute=absolute) + "\">"
                    ret += title + "</a>"
                else:
                    ret += "[bad story: " + x.group(0) + "]"


            elif uri == "topic":

                topic = gruta.topic(x.group(2))

                if topic:
                    ret += "<a href=\"" + gruta.url(topic, absolute=absolute) + "\">"
                    ret += topic.get("name") + "</a>"
                else:
                    ret += "[bad topic: " + x.group(0) + "]"


            elif uri == "link" or uri == "links":

                url = x.group(1).replace("link", "http") + "://" + x.group(2)

                try:
                    title = special_uris(gruta, x.group(3), 0, absolute)
                except:
                    title = url

                ret += "<a href=\"" + url + "\">" + title + "</a>"


            elif uri == "img":

                try:
                    ret += "<div class=\"%s\"><img src=\"%simg/%s\" alt=\"\"/></div>" % (
                        x.group(3), gruta.url(absolute=absolute), x.group(2))
                except:
                    ret += "<img src=\"%simg/%s\" alt=\"\"/>" % (
                        gruta.url(absolute=absolute), x.group(2))


            elif uri == "thumb":

                s = "<a href=\"%simg/%s\">" % (
                    gruta.url(absolute=absolute), x.group(2))

                s += "<img src=\"%simg/%s\" alt=\"\" class=\"thumb\"/>" % (
                    gruta.url(absolute=absolute), x.group(2))

                s += "</a>"

                try:
                    ret += "<span class=\"%s\">%s</span>" % (x.group(3), s)
                except:
                    ret += s


            elif uri == "body":

                story = gruta.story(x.group(2), x.group(3))

                if story:
                    ret += "<h3>" + story.get("title") + "</h3>\n"
                    ret += special_uris(gruta, story.get("body"), 0, absolute)
                else:
                    ret += "[bad story: " + x.group(0) + "]"


            elif uri == "h-card":

                uid = x.group(2)

                user = gruta.user(uid)

                if user is not None:
                    ret += "<div class=\"h-card\">\n<p>"

                    if user.get("url") != "":
                        ret += "<a class=\"u-url url\" rel=\"me\" href=\"%s\">" % user.get("url")
                        ret += "<span class=\"p-name uid\">%s</span></a>" % user.get("username")
                    else:
                        ret += "<span class=\"p-name uid\">%s</span>" % user.get("username")

                    ret += " &lt;<a class=\"u-email\" href=\"mailto:%s\">%s</a>&gt;</p>\n" % (
                        user.get("email"), user.get("email"))

                    if user.get("avatar") != "":
                        ret += "<img class=\"u-photo\" src=\"%s\" alt=\"\"/>\n" % user.get("avatar")

                    if user.get("bio") != "":
                        ret += "<p class=\"p-note\">%s</p>\n" % user.get("bio")

                    ret += "</div>\n"
                else:
                    ret += "[bad user: " + uid + "]"


            elif uri == "user":

                uid = x.group(2)

                user = gruta.user(uid)

                if user is not None:
                    ret += "<a href=\"%s\">%s</a>" % (
                        gruta.url(user), user.get("username"))

                else:
                    ret += "[bad user: %s]" % uid


            elif uri == "tag":

                tag = x.group(2)

                try:
                    lbl = x.group(3)
                except:
                    lbl = tag

                if tag is not None:
                    lnk = "%s.html" % tag
                else:
                    lbl = "Tags"
                    lnk = "index.html"

                ret += "<a href=\"%s\">%s</a>" % (
                    gruta.url("/tag/%s" % lnk), lbl)


            # convert last part: it can contain the same uri
            # (but not up in the regex list)
            ret += special_uris(gruta, post, e, absolute)

    return ret
