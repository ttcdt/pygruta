#
#   pygruta CMS
#   ttcdt <dev@triptico.com>
#
#   This software is released into the public domain.
#

# command-line interface

import sys, os, time
import pygruta

def usage():
    print("pygruta %s - command-line interface to Gruta CMS databases" % pygruta.__version__)
    print("ttcdt <dev@triptico.com>")
    print("This software is released into the public domain.\n")

    print("Usage:")
    print("  pygruta {command} {gruta_source} [options]\n")

    print("Commands:\n")

    print("create {src} [user] [topic]                Creates Gruta source, with optional")
    print("                                           default user id and first topic")
    print("topics {src}                               Lists all topics")
    print("stories {src} {topic_id}                   Lists all stories from a topic")
    print("post {src} [{topic_id}] [{id}] [-e]        Posts a story from STDIN")
    print("                                           or edited in $EDITOR if -e")
    print("story {src} {topic_id} {id}                Dumps a story to STDOUT")
    print("delete-story {src} {topic_id} {id}         Deletes a story")
    print("snapshot {src} {out folder} [url_prefix]   Snapshots a Gruta site")
    print("snap-url-list {src} {out folder}           Lists the URLs to be snapshotted")
    print("snap-url {src} {out folder} {url_prefix} \\")
    print("    {url} [url...]                         Snapshots URLs one by one")
    print("httpd {src} [port]                         Runs the httpd")
    print("webmention-feed {src}                      Sends Webmentions to links in the feed")
    print("twitter-feed {src}                         Sends the feed to Twitter")
    print("twitter-import {src} -q {query} \\          Imports tweets from query(s),")
    print("    [-i {ignore}] [-q {q} -i {i}...]       optionally ignoring tweeter(s)")
    print("activitypub-feed {src}                     Sends the feed to ActivityPub followers")
    print("activitypub-send-note {src} {uid} \\        Sends an ActivityPub note")
    print("    {actor_url} {msg}")
    print("activitypub-like {src} {uid} {post}        Likes a post")
    print("activitypub-send-story {src} \\             Sends a story as an ActivityPub note")
    print("    {actor_url} {topic_id} {id}")
    print("search {src} 'query string'                Searches stories by content")
    print("icalendar-import {src} {file.ics}          Imports an iCalendar into 'events' topic")
    print("icalendar-export {src}                     Exports the 'events' topic as an iCalendar")
    print("copy {src} {dest}                          Copies the 'src' db into 'dest'")
    print("atom {src}                                 Prints an ATOM feed to STDOUT")
    print("feeds {src}                                Sends all feeds")
    print("short-url {src} {url}                      Returns a shortened URL")
    print("gemini-snapshot {src} {outdir}             Creates a Gemini snapshot")

    return 1


def story_to_lines(story):

    for f in story.fields:
        if f not in ("abstract", "body", "content"):
            fc = story.get(f)

            if f == "tags":
                fc = ",".join(fc)

            yield f + ": " + fc

    yield ""
    yield story.get("content")


def lines_to_story(story, lines):

    data      = {}
    content   = []
    in_header = True

    # iterate the lines collecting data
    for l in lines:
        l = l.replace("\n", "")

        if in_header:
            if l == "":
                in_header = False
            else:
                try:
                    key, value = l.split(": ", 1)

                    data[key] = value

                except:
                    pygruta.log("ERROR", "Invalid line '%s'" % l)
        else:
            content.append(l)

    for key, value in data.items():
        if key == "tags":
            if value == "":
                value = []
            else:
                value = value.split(",")

        story.set(key, value)

    story.set("content", "\n".join(content))


def main():
    ret = 0

    import pygruta

    os.umask(0o0002)

    args = sys.argv
    args.reverse()
    args.pop()

    if len(args) < 2:
        ret = usage()
    else:
        cmd   = args.pop()
        gruta = pygruta.open(args.pop())
    
        # debug?
        try:
            gruta.debug = int(os.environ["DEBUG"])
        except:
            pass
    
        if cmd == "topics":
            for t in gruta.topics():
                print(t)
    
        elif cmd == "stories":
            if len(args) < 1:
                ret = usage()
            else:
                for s in gruta.stories(args.pop()):
                    print(s)
    
        elif cmd == "snapshot":
            if len(args) < 1:
                ret = usage()
            else:
                outdir = args.pop()
    
                if len(args):
                    url_prefix = args.pop()
                else:
                    url_prefix = ""
    
                from pygruta.snapshot import snapshot
    
                snapshot(gruta, outdir, url_prefix)

        elif cmd == "snap-url-list":
            if len(args) < 1:
                ret = usage()
            else:
                outdir = args.pop()
    
                if len(args):
                    url_prefix = args.pop()
                else:
                    url_prefix = ""
    
                from pygruta.snapshot import url_list
    
                for f in url_list(gruta, outdir):
                    print(f.replace(" ", "%20"))

        elif cmd == "snap-url":
            if len(args) < 3:
                ret = usage()
            else:
                outdir     = args.pop()
                url_prefix = args.pop()
    
                import pygruta.snapshot

                gruta.url_prefix     = url_prefix
                pygruta.snapshot.set_outdir(gruta, outdir)

                for url in args:
                    pygruta.snapshot.snap_url(gruta, outdir, url)

        elif cmd == "httpd":
            import pygruta.httpd
    
            if len(args):
                port = int(args.pop())
            else:
                port = 8000
    
            pygruta.httpd.httpd(gruta, port=port)
    
        elif cmd == "create":
            if len(args):
                uid = args.pop()
            else:
                uid = None
    
            if len(args):
                topic_id = args.pop()
            else:
                topic_id = None
    
            gruta.create(uid, topic_id)
    
        elif cmd == "activitypub-feed":
            import pygruta.activitypub
    
            pygruta.activitypub.send_feed(gruta)
    
        elif cmd == "webmention-feed":
            import pygruta.webmention
    
            pygruta.webmention.send_feed(gruta)
    
        elif cmd == "twitter-feed":
            import pygruta.twitter
    
            pygruta.twitter.send_feed(gruta)
    
        elif cmd == "feeds":
            import pygruta.activitypub
            pygruta.activitypub.send_feed(gruta)
    
            import pygruta.webmention
            pygruta.webmention.send_feed(gruta)
    
            import pygruta.twitter
            pygruta.twitter.send_feed(gruta)
    
        elif cmd == "activitypub-send-note":
            import pygruta.activitypub
    
            if len(args) < 3:
                ret = usage()
            else:
                uid  = args.pop()
                dest = args.pop()
                text = args.pop()
    
                user = gruta.user(uid)
    
                if user is None:
                    pygruta.log("ERROR", "bad user id: " + uid)
                    ret = 10
                else:
                    note = pygruta.activitypub.note(gruta, user, dest=dest, message=text)
    
                    pygruta.activitypub.send_note_to_actor(gruta, user, dest, note)
    
    
        elif cmd == "activitypub-like":
            import pygruta.activitypub
    
            if len(args) < 2:
                ret = usage()
            else:
                uid = args.pop()
                url = args.pop()
    
                user = gruta.user(uid)
    
                if user is None:
                    pygruta.log("ERROR", "bad user id: " + uid)
                    ret = 10
                else:
                    pygruta.activitypub.react(gruta, user, url)
    
    
        elif cmd == "activitypub-send-story":
            import pygruta.activitypub

            if len(args) < 3:
                ret = usage()
            else:
                dest     = args.pop()
                topic_id = args.pop()
                id       = args.pop()
    
                story_o = gruta.story(topic_id, id)

                if story_o is None:
                    pygruta.log("ERROR", "Bad story %s/%s" % (topic_id, id))
                    ret = 10
                else:
                    user_o = gruta.user(story_o.get("userid"))

                    note = pygruta.activitypub.note_from_story(gruta, story_o)

                    pygruta.activitypub.send_note_to_actor(gruta, user_o, dest, note)


        elif cmd == "twitter-import":
            import pygruta.twitter
    
            queries     = []
            ignore_from = []
    
            while len(args):
                o = args.pop()
    
                if o == "-q":
                    queries.append(args.pop())
                elif o == "-i":
                    ignore_from.append(args.pop().lower())
                else:
                    pygruta.log("ERROR", "unrecognized argument: " + args[i])
                    ret = 10
                    queries = []
                    break
    
            if len(queries):
                pygruta.twitter.import_tweets(gruta, queries, ignore_from)
    
        elif cmd == "search":
    
            if len(args) < 1:
                ret = usage()
            else:
                content = args.pop()
    
                for s in gruta.story_set(content=content, timeout=2):
                    print(s[0], s[1])
    
    
        elif cmd == "story":
    
            if len(args) < 2:
                ret = usage()
            else:
                topic_id = args.pop()
                id       = args.pop()
    
                story = gruta.story(topic_id, id)
    
                if story is None:
                    pygruta.log("ERROR", "bad story " + topic_id + "/" + id)
                    ret = 10
                else:
                    for s in story_to_lines(story):
                        print(s)
    
    
        elif cmd == "delete-story":
    
            if len(args) < 2:
                ret = usage()
            else:
                topic_id = args.pop()
                id       = args.pop()
    
                story = gruta.story(topic_id, id)
    
                if story is None:
                    pygruta.log("ERROR", "bad story " + topic_id + "/" + id)
                    ret = 10
                else:
                    gruta.delete_story(story)
    
    
        elif cmd == "post":
    
            ids     = []
            editor  = False
            story   = None
            tmpfile = ""
    
            while len(args):
                a = args.pop()
    
                if a == "-e":
                    editor = True
                else:
                    ids.append(a)
    
            if len(ids) >= 2:
                story = gruta.story(ids[0], ids[1])
    
            elif len(ids) >= 1:
                if gruta.topic(ids[0]):
                    story = gruta.new_story({"topic_id": ids[0]})
    
            else:
                story = gruta.new_story()
    
            if story is None:
                pygruta.log("ERROR", "bad topic or story")
                ret = 10
    
            else:
                gruta.story_defaults(story)
    
                if editor:
                    tmpfile = "/tmp/pygruta-post-%f.html" % time.time()
    
                    with open(tmpfile, "w") as f:
                        for l in story_to_lines(story):
                            f.write(l + "\n")
    
                    # pick current mtime
                    mtime = os.stat(tmpfile).st_mtime
    
                    # call editor
                    os.system("$EDITOR " + tmpfile)
    
                    if os.stat(tmpfile).st_mtime > mtime:
                        # file was touched? read it
                        lines_to_story(story, open(tmpfile, "r"))
    
                    else:
                        # nothing to do
                        story = None
    
                else:
                    lines_to_story(story, sys.stdin)
    
                if story is not None:
                    if len(ids) >= 1:
                        story.set("topic_id", ids[0])
    
                    if len(ids) >= 2:
                        story.set("id", ids[1])
    
                    story = gruta.save_story(story)
    
                    if story is None:
                        pygruta.log("ERROR", "Error saving story")
    
                        if tmpfile != "":
                            pygruta.log("INFO", "Story in " + tmpfile)
    
                        ret = 10
                    else:
                        pygruta.log("INFO", "Saved story " + story.get("topic_id") + "/" +     story.get("id"))
    
                        # delete tmpfile
                        try:
                            os.unlink(tmpfile)
                        except:
                            pass
    
        elif cmd == "icalendar-import":
    
            import pygruta.calendar
    
            if len(args) == 0:
                ret = usage()
            else:
                ics = args.pop()
    
                try:
                    fd = open(ics, "r")
                except:
                    pygruta.log("ERROR", "Cannot open calendar file " + ics)
                    ret = 10
                    fd = None
    
                if fd is not None:
                    pygruta.calendar.import_icalendar(gruta, fd)
    
    
        elif cmd == "icalendar-export":
    
            import pygruta.calendar
    
            for l in pygruta.calendar.export_icalendar(gruta):
                print(l, end="\r\n")
    
    
        elif cmd == "atom":
    
            import pygruta.xml
    
            print(pygruta.xml.atom(gruta, gruta.feed()))
    
    
        elif cmd == "copy":
    
            if len(args) < 1:
                ret = usage()
            else:
                org = pygruta.open(args.pop())
                org.copy(gruta)
                org.close()

        elif cmd == "short-url":

            if len(args) < 1:
                ret = usage()
            else:
                l_url = args.pop()
                print(gruta.shorten_url(l_url))

        elif cmd == "gemini-snapshot":

            if len(args) < 1:
                ret = usage()
            else:
                outdir = args.pop()

                import pygruta.gemini
                pygruta.gemini.snapshot(gruta, outdir)
    
        else:
            pygruta.log("ERROR", "invalid command: " + cmd)
            ret = 2
    
        gruta.close()
    
    return ret

if __name__ == "__main__":
    sys.exit(main())
