#
#   pygruta CMS
#   ttcdt <dev@triptico.com>
#
#   This software is released into the public domain.
#

#   Gemini support

import re, glob, os

def to_html(content):
    """ converts a text in Gemini (Gemtext) format to HTML """

    title  = ""
    body   = ""
    in_pre = False

    # iterate by lines
    for l in content.split("\n"):
        if l.startswith("###"):
            x = re.search(r"^###\s*(.*)$", l)
            l = "<h3>" + x.group(1) + "</h3>"

        elif l.startswith("##"):
            x = re.search(r"^##\s*(.*)$", l)
            l = "<h2>" + x.group(1) + "</h2>"

        elif l.startswith("#"):
            x = re.search(r"^#\s*(.*)$", l)
            title = x.group(1)
            l = None

        elif l == "```":
            if in_pre:
                l = "</pre>"
            else:
                l = "<pre>"

            in_pre = not in_pre

        elif l.startswith("=>"):
            # link
            x = re.search(r"^(=>)\s?([^ ]+)\s?(.*)$", l)

            try:
                url = x.group(2)
                lbl = x.group(3)

                if lbl == "":
                    lbl = url

                l = "<p><a href=\"%s\">%s</a></p>" % (url, lbl)
            except:
                l = None

        elif l.startswith("*"):
            x = re.search(r"^\*\s?(.*)$", l)

            l = "<p>&bull; " + x.group(1) + "</p>"

        elif l.startswith(">"):
            x = re.search(r"^>\s?(.*)$", l)

            l = "<blockquote>\n<p><q>" + x.group(1) + "</q></p>\n</blockquote>"

        else:
            if not in_pre and l != "":
                l = "<p>" + l + "</p>"

        if l is not None:
            body += l + "\n"

    return title, body, body


def snapshot(gruta, outdir):
    """ A very simple snapshotting of Gemini files """

    # ensure there is a trailing /
    if outdir[-1] != "/":
        outdir += "/"

    # get all currently existent files
    gruta.snapshot_files = glob.glob(outdir + "**", recursive=True)
    gruta.snapshot_files.remove(outdir)
    gruta.snapshot_outdir = outdir

    def d(file):
        try:
            gruta.snapshot_files.remove(gruta.snapshot_outdir + file)
        except:
            pass

        return gruta.snapshot_outdir + file

    # create index
    index = open(d("index.gmi"), "w")
    gruta.log("INFO", "Gemini snapshot: CREATE index.gmi")

    index.write("# %s\n\n" % gruta.template("cfg_site_name"))
    index.write("## %s\n\n" % gruta.template("cfg_slogan"))

    # iterate all stories
    for si in gruta.story_set():
        t = si[0]
        s = si[1]

        story = gruta.story(t, s)

        # only snapshot stories in gemini format
        if story.get("format") == "gemini":
            # get author
            user = gruta.user(story.get("userid"))

            gmi = open(d("%s.gmi" % s), "w")
            gruta.log("INFO", "Gemini snapshot: CREATE %s.gmi" % s)

            gmi.write("# %s\n\n" % story.get("title"))
            gmi.write("%s %s\n\n" % (
                gruta.date_format(story.get("date"), "%Y-%m-%d"),
                user.get("username")
                )
            )
            gmi.write(story.get("content") + "\n")
            gmi.write("=> index.gmi Back\n")

            # write story into index
            index.write("=> %s.gmi %s\n" % (s, story.get("title")))

    for f in list(gruta.snapshot_files):
        try:
            os.unlink(f)
            gruta.log("INFO", "Gemini snapshot: DELETE %s" % f)
        except:
            pass
