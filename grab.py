#!/usr/bin/env python3
# -*- coding: utf-8; -*-

import sys, os
import re
import urllib.parse
import time
import copy
import typing

import requests
import lxml.html
import lxml.etree as etree

CacheDir = "cache"
UrlRoot = "https://gamefaqs.gamespot.com/switch/230454-hyrule-warriors-definitive-edition/faqs/73095/"

Chapters = [
    "introduction",
    "unlockables-by-character",
    "my-fairy-unlockables",
    "gold-skulltula-locations",
    "legend-mode",
    "adventure-mode-overview",
    "adventure-map",
    "rewards-map",
    "great-sea-map",
    "master-quest-map",
    "twilight-map",
    "termina-map",
    "master-wind-waker-map",
    "koholint-island-map",
    "grand-travels-map",
    "lorule-map",
]

def appendAll(node, things):
    """Given `things`, a list of XML elements or strings, append elements to XML
    `node` as subelements, and append the strings as texts, in the order given
    in the list.
    """
    if len(things) == 0:
        return

    List = things
    if isinstance(things[0], str):
        if len(node) == 0:
            if node.text:
                node.text = node.text + things[0]
            else:
                node.text = things[0]
            List = things[1:]
    else:
        for Ele in List:
            if isinstance(Ele, str):
                node[-1].tail = Ele
            else:
                node.append(Ele)

def dropTag(node):
    def _preserve_tail_before_delete(node):
        if node.tail: # preserve the tail
            previous = node.getprevious()
            if previous is not None:
                # if there is a previous sibling it will get the tail
                if previous.tail is None:
                    previous.tail = node.tail
                else:
                    previous.tail = previous.tail + node.tail
            else: # The parent get the tail as text
                parent = node.getparent()
                if parent.text is None:
                    parent.text = node.tail
                else:
                    parent.text = parent.text + node.tail

    Children = copy.copy(node.xpath("child::node()"))
    Parent = node.getparent()
    _preserve_tail_before_delete(node)
    Parent.remove(node)
    appendAll(Parent, Children)

def removeToc(html):
    TocNodes = html.xpath('//div[@class = "ftoc"]')
    if TocNodes:
        for Node in TocNodes:
            Node.getparent().remove(Node)

def dealWithLinks(html, current_chapter):
    for Link in html.xpath("//a"):
        UrlRaw = Link.get("href", "") # type: str
        Url = urllib.parse.urlparse(UrlRaw)
        if Url.path.startswith('/'): # Not a relative url.
            continue

        TargetChapter = Url.path
        TargetSection = Url.fragment

        if len(TargetChapter) > 0:
            Link.attrib["target-chapter"] = TargetChapter
        else:
            Link.attrib["target-chapter"] = current_chapter

        if len(TargetSection) > 0:
            Link.attrib["target-section"] = TargetSection
        elif "target-section" in Link:
            del Link.attrib["target-section"]

def platformFromImgTag(img_tag):
    if img_tag.get("src") == "https://gamefaqs.akamaized.net/faqs/95/73095-150.png":
        return "3ds"
    elif img_tag.get("src") == "https://gamefaqs.akamaized.net/faqs/95/73095-151.png":
        return "switch"
    else:
        return None

def htmlPreprocess(html_raw):
    Node = etree.HTML(html_raw)
    Result = etree.tostring(Node, pretty_print=True, method="xml", encoding=str)

    DocType = "<!doctype html>"
    if Result.startswith(DocType):
        Result = Result[len(DocType):].lstrip()

    NewLine = Result.find('\n')
    Result = "<html>" + Result[NewLine:]
    Result = re.sub(r'<((img|br|meta|link|input)[^>]*[^/])>', r"<\1 />", Result)
    Result = Result.replace("&rsquo;", '’')
    Result = Result.replace("&squo;", '‘')
    Result = Result.replace("&nbsp;", ' ')
    Result = Result.replace("&ndash;", '-')
    Result = Result.replace("&raquo;", '»')

    return Result

def dealWith3dsSwitchPre(html_raw):
    Result = re.sub(r'\( *?<img[^>]*? src="https://gamefaqs\.akamaized\.net/faqs/95/73095-150\.png"[^>]*?/>([^|<]+?)[|] *?<img[^>]*? src="https://gamefaqs\.akamaized\.net/faqs/95/73095-151\.png"[^>]*?/>([^\)]*?)\)',
                    r'<div grab_tag="platform-specific"><div grab_tag="platform" grab_name="3ds">\1</div><div grab_tag="platform" grab_name="switch">\2</div></div>',
                    html_raw)

    Result = re.sub(r'<img[^>]*? src="https://gamefaqs\.akamaized\.net/faqs/95/73095-150\.png"[^>]*?/>([^|<]+?)[|] *?<img[^>]*? src="https://gamefaqs\.akamaized\.net/faqs/95/73095-151\.png"[^>]*?/>([^<]*?)<',
                    r'<div grab_tag="platform-specific"><div grab_tag="platform" grab_name="3ds">\1</div><div grab_tag="platform" grab_name="switch">\2</div></div><',
                    Result)
    return Result

def dealWithTempTags(html):
    for Node in html.xpath("//div[@grab_tag]"):
        for Attr in Node.keys():
            if Attr.startswith("grab_"):
                if Attr == "grab_tag":
                    Node.tag = Node.get(Attr)
                else:
                    Node.set(Attr[5:], Node.get(Attr))
                Node.attrib.pop(Attr)

def dealWith3dsSwitch(html):
    for ImgTag in html.xpath('//img'):
        if ImgTag.getparent() is None:
            # Ghost tags...
            continue

        if ImgTag.getparent().tag == "platform" or ImgTag.getparent().tag == "platform-specific":
            continue
        Platform = platformFromImgTag(ImgTag)
        if Platform is None:
            continue

        # Switch/3ds disclaimer in the first paragraph
        if ImgTag.getparent().tag == "p":
            Para = ImgTag.getparent()
            if Para.getprevious() is not None and Para.getprevious().tag == "h2":
                Para.getparent().remove(Para)

        PlatformRoot = etree.Element("platform-specific")
        PlatformNode = etree.SubElement(PlatformRoot, "platform", name=Platform)
        ToDelete = []

        Next = ImgTag.getnext()
        PlatformNode.append(copy.copy(ImgTag))
        ToDelete.append(ImgTag)
        BrOccurred = False
        while Next is not None:
            if Next.tag == "br":
                BrOccurred = True
            else:
                if Next.tag == "img":
                    Platform = platformFromImgTag(Next)
                    if Platform is not None:
                        PlatformNode = etree.SubElement(PlatformRoot, "platform",
                                                        name=Platform)
                PlatformNode.append(copy.copy(Next))
            ToDelete.append(Next)
            Next = Next.getnext()

        if BrOccurred:
            ImgTag.addprevious(PlatformRoot)
            for Node in ToDelete:
                Node.getparent().remove(Node)
        else:
            PlatformRoot = etree.Element("platform-specific")
            PlatformNode = etree.SubElement(PlatformRoot, "platform",
                                            name=platformFromImgTag(ImgTag))
            PlatformNode.append(copy.copy(ImgTag))
            ImgTag.addprevious(PlatformRoot)
            ImgTag.getparent().remove(ImgTag)

    for ImgTag in html.xpath('//img'):
        if ImgTag.getparent().tag == "platform" or ImgTag.getparent().tag == "platform-specific":
            if platformFromImgTag(ImgTag) is not None:
                dropTag(ImgTag)

def extractMapInfo(table_tag):
    def hasBr(element):
        for SubEle in element:
            if SubEle.tag == "br":
                return True
        return False

    AllProps = {"Mission": "mission", "A-Rank Victory": "loot-a",
                "Battle Victory": "loot-v", "Treasure": "treasure",
                "A-Rank KOs": "ko-a", "A-Rank Time": "time-a",
                "A-Rank Damage": "damage-a"}
    MapInfo = dict()
    Body = table_tag.find("tbody")
    Mode = None
    Props = []
    for Row in Body:
        Cols = list(Row)
        if Cols[0].tag == "th":
            for Col in Cols:
                Item = Col.text.strip()
                if Item in AllProps:
                    Props.append(AllProps[Item])
            Mode = "info"
            continue
        elif Cols[0].tag == "td":
            if len(Cols) != len(Props):
                Props = []
                continue

            for i in range(len(Cols)):
                Content = Cols[i].xpath("child::node()")
                if len(Cols[i]) > 0:
                    # Is this value a <br> seperated list?
                    if hasBr(Cols[i]):
                        # It's a <br> seperated list.
                        ContentRaw = copy.copy(Content)
                        Content = []
                        for Entry in ContentRaw:
                            if isinstance(Entry, str):
                                NewEle = etree.Element("item")
                                NewEle.text = Entry
                                Content.append(NewEle)
                            elif Entry.tag != "br":
                                Content.append(Entry)

                MapInfo[Props[i]] = Content
            Props = []

    return MapInfo

def dealWithMapTables(html):
    Infos = []
    Title = html.xpath('//div[@id = "faqwrap"]/h2')[0].text.strip()
    Match = re.match(r"(.+) Map", Title)
    if not Match:
        return
    Title = Match.group(1)

    for Table in html.xpath('//table[@class = "ffaq"]'):
        TableTitle = Table.getprevious()
        if TableTitle.tag != "h4":
            continue
        Match = re.match(r"(.+) Map (.+)-(.+)", TableTitle.text.strip())
        if Match:
            Name = Match.group(1)
            Col = Match.group(2)
            Row = Match.group(3)
            Info = extractMapInfo(Table)
            Infos.append({"name": Name, "col": Col, "row": Row, "info": Info})

    return {"title": Title, "info": Infos}

def dealWithMapTileTables(html):
    def matchStyleWithSubEle(element, pattern):
        try:
            Match = re.search(pattern, element.get("style"))
        except Exception:
            return None
        else:
            if Match:
                return Match.group(1)
            elif len(element) == 0:
                return None
            else:
                return matchStyleWithSubEle(element[0], pattern)

    Colors = {"000000": 0, "008000": 1, "ff9900": 2, "800080": 3, "ff6600": 4,
              "0000ff": 5, "ff0000": 6}
    TheTable = None
    for Table in html.xpath('//table[@class = "ffaq"]'):
        Body = Table[0]
        if Body.tag != "tbody":
            continue

        if len(Body) < 5:
            continue

        if len(Body[0]) < 6:
            continue

        # Span = Body[0][0][0]
        # if "style" not in Span.attrib:
        #     continue

        # try:
        #     InnerSpan = Span[0][0]
        # except Exception:
        #     continue

        TheTable = Table
        break

    if TheTable is None:
        return

    TileDifficulty = {}
    Tiles = TheTable.xpath("tbody/tr/td//a")
    for LinkNode in Tiles:
        Span = LinkNode.getparent()
        Color = matchStyleWithSubEle(Span, r'background-color: #([0-9a-f]+);')
        if Color is None:
            Color = matchStyleWithSubEle(LinkNode, r'background-color: #([0-9a-f]+);')
            if Color is None:
                print("Warning: no difficulty found at tile {}...".format(LinkNode.text))
                continue

        if len(LinkNode) > 0:
            Name = LinkNode[0].text.strip()
        else:
            Name = LinkNode.text.strip()
        Name = Name[0] + Name[2]
        if Color not in Colors:
            raise KeyError("Unknown color: " + Color)

        TileDifficulty[Name] = Colors[Color]

    return TileDifficulty

MapInfoRoot = etree.Element("maps")

def dealWithChapter(name):
    global MapInfoRoot

    CacheFileName = os.path.join(CacheDir, name + ".xml")
    if os.path.exists(CacheFileName):
        with open(CacheFileName, 'r') as f:
            Content = f.read()

        Content = dealWith3dsSwitchPre(Content)
        Html = etree.XML(Content)
    else:
        Headers = {'user-agent': 'my-grab/0.0.1'}
        print("Downloading {}...".format(name))
        Res = requests.get(UrlRoot + name, headers=Headers)
        HtmlRaw = Res.text.replace("\r", "")
        HtmlRaw = htmlPreprocess(HtmlRaw)
        HtmlRaw = dealWith3dsSwitchPre(HtmlRaw)

        Html = etree.XML(HtmlRaw)
        # Html = lxml.html.document_fromstring(HtmlRaw)
        Html = Html.xpath('//div[@id = "faqwrap"]')[0]
        time.sleep(2)

    removeToc(Html)
    dealWithTempTags(Html)
    dealWithLinks(Html, name)
    dealWith3dsSwitch(Html)
    if name.endswith("-map"):
        MapNode = etree.SubElement(MapInfoRoot, "map")
        Map = dealWithMapTables(Html)
        MapNode.set("name", Map["title"])
        Difficulty = dealWithMapTileTables(Html)
        TilesNode = etree.SubElement(MapNode, "tiles")
        for Tile in Map["info"]:
            TileNode = etree.SubElement(TilesNode, "tile")
            Coord = Tile["col"] + Tile["row"]
            TileNode.attrib["coordinate"] = Coord

            for Prop in Tile["info"]:
                PropNode = etree.SubElement(TileNode, Prop)
                # Deep copy here. Because stuff in `Tile["info"][Prop]` actually
                # point to the original HTML elements/text in the HTML node
                # tree.
                PropValue = copy.deepcopy(Tile["info"][Prop])
                appendAll(PropNode, PropValue)
                if PropNode.text == "None" or PropNode.text == "N/A":
                    PropNode.text = None
                if len(PropNode) == 1 and PropNode[0].tag == 'p':
                    dropTag(PropNode[0])
            if (Difficulty is not None) and (Coord in Difficulty):
                    etree.SubElement(TileNode, "difficulty").text = str(Difficulty[Coord])


    if not os.path.exists(CacheDir):
        os.makedirs(CacheDir)
    with open(CacheFileName, 'wb') as f:
        # Write as XML.
        f.write(etree.tostring(Html, pretty_print=True, method="xml"))

for Chapter in Chapters:
    dealWithChapter(Chapter)
with open("maps.xml", 'wb') as MapFile:
    MapFile.write(etree.tostring(MapInfoRoot, xml_declaration=True,
                                 encoding="utf-8",
                                 pretty_print=True))
