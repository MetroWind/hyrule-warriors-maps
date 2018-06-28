#!/usr/bin/env python3
# -*- coding: utf-8; -*-

import lxml.etree as Etree

def safeInt(x):
    try:
        y = int(x)
    except Exception:
        return x
    else:
        return y

class SvgQName(object):
    def __init__(self):
        self.SvgNs = "http://www.w3.org/2000/svg"
        self.NsMap = {None: self.SvgNs,} # "xlink": "http://www.w3.org/1999/xlink"}

    def __call__(self, short_name):
        return "{{{}}}{}".format(self.SvgNs, short_name)

qname = SvgQName()

DiffiColors = ("#bdc3c7", "#27ae60", "#f1c40f", "#8e44ad", "#e67e22", "#2980b9",
               "#c0392b")

class TileInfo(object):
    def __init__(self):
        self.Coord = ""         # 1-based
        self.Mission = ""
        self.LootA = None
        self.LootV = None
        self.KoA = None
        self.TimeA = None
        self.DamageA = None
        self.Treasure = None
        self.Difficulty = 0

    @property
    def CoordNum(self):
        """(Column, row) in number."""
        return (ord(self.Coord[0]) - ord('A') + 1,
                int(self.Coord[1]))

    @classmethod
    def fromNode(cls, node):
        def processSubNode(subnode):
            if len(subnode) == 0:
                # This node has just text. Return the text.
                if subnode.text:
                    return subnode.text.strip()
                else:
                    return None
            else:
                # This node has subnode. It could be a platform-specific value,
                # or multiple items.
                if subnode[0].tag == "platform-specific":
                    Node = subnode.xpath('platform-specific/'
                                         'platform[@name = "switch"]')
                    if Node:
                        return processSubNode(Node[0])

                elif subnode[0].tag == "item":
                    return [processSubNode(ItemNode) for ItemNode in subnode]
                else:
                    return None

        Tile = cls()
        Tile.Coord = node.get("coordinate")
        for SubNode in node:
            if SubNode.tag == "mission":
                Tile.Mission = processSubNode(SubNode)
            elif SubNode.tag == "loot-a":
                Tile.LootA = processSubNode(SubNode)
            elif SubNode.tag == "loot-v":
                Tile.LootV = processSubNode(SubNode)
            elif SubNode.tag == "treasure":
                Tile.Treasure = processSubNode(SubNode)
            elif SubNode.tag == "ko-a":
                Tile.KoA = safeInt(processSubNode(SubNode))
            elif SubNode.tag == "time-a":
                Tile.TimeA = processSubNode(SubNode)
            elif SubNode.tag == "damage-a":
                Tile.DamageA = safeInt(processSubNode(SubNode))
            elif SubNode.tag == "difficulty":
                Tile.Difficulty = int(processSubNode(SubNode))
        return Tile

    def nodeSvg(self, cell_width, cell_height, map_name):
        TileNode = Etree.Element(qname('g'))
        RectNode = Etree.SubElement(
            TileNode, qname('rect'),

            fill=DiffiColors[self.Difficulty],
            x=str((self.CoordNum[0] - 1) * cell_width + 0.5),
            y=str((self.CoordNum[1] - 1) * cell_height + 0.5),
            width=str(cell_width),
            height=str(cell_height))
        RectNode.set("class", "TileBG")
        RectNode.set("id", "TileBG-{}-{}".format(map_name, self.Coord))

        TextNode = Etree.SubElement(
            TileNode, qname("text"),
            x=str((self.CoordNum[0] - 0.5) * cell_width),
            y=str((self.CoordNum[1] - 0.5) * cell_height + 5),
            fill="white")
        TextNode.text = self.Coord
        TextNode.set("class", "TileText")
        TextNode.set("id", "TileText-{}-{}".format(map_name, self.Coord))
        TextNode.set("font-family", '"IBM Plex Mono", "Source Code Pro", '
                     'Inconsolata, Consolas, monospace')
        TextNode.set("font-weight", 'normal')
        TextNode.set("font-size", "12")
        TextNode.set("text-anchor", "middle")

        BtnNode = Etree.SubElement(
            TileNode, qname('rect'),
            fill="transparent",
            x=str((self.CoordNum[0] - 1) * cell_width + 0.5),
            y=str((self.CoordNum[1] - 1) * cell_height + 0.5),
            width=str(cell_width),
            height=str(cell_height))
        BtnNode.set("class", "TileBtn")
        BtnNode.set("id", "TileBtn-{}-{}".format(map_name, self.Coord))
        return TileNode

    def html(self, map_name):
        Lines = ["<div>",]
        Lines.append("<h2>{} Map {}</h2>".format(map_name, self.Coord))
        Lines.append("<table>")
        Lines.append("<tbody>")
        Lines.append("<tr><td>Mission</td><td>{}</td></tr>".format(self.Mission))
        if self.LootV:
            Lines.append("<tr><td>Loot</td><td>{}</td></tr>".format(self.LootV))
        if self.Treasure:
            Lines.append("<tr><td>Treasure</td><td>{}</td></tr>".format(self.Treasure))
        if self.LootA:
            Lines.append("<tr><td>A-rank loot</td><td>{}</td></tr>".format(self.LootA))
        if self.KoA:
            Lines.append("<tr><td>A-rank KO</td><td>{}</td></tr>".format(self.KoA))
        if self.TimeA:
            Lines.append("<tr><td>A-rank time</td><td>{}</td></tr>".format(self.TimeA))
        if self.DamageA:
            Lines.append("<tr><td>A-rank damage</td><td>{}</td></tr>".format(self.DamageA))
        Lines.append("</tbody></table>")
        Lines.append("</div>")
        return Lines

class MapInfo(object):
    def __init__(self):
        self.Tiles = {}
        self._MaxCorner = None
        self.Title = ""

    def addTile(self, tile):
        self.Tiles[tile.Coord] = tile
        if self._MaxCorner is None:
            self._MaxCorner = tile.Coord
        else:
            if tile.Coord > self._MaxCorner:
                self._MaxCorner = tile.Coord
        return self

    @property
    def Cols(self):
        return ord(self._MaxCorner[0]) - ord('A') + 1

    @property
    def Rows(self):
        return int(self._MaxCorner[1])

    def genSvg(self):
        CellWidth = 30
        CellHeight = 20

        Root = Etree.Element(qname("svg"), nsmap=qname.NsMap)
        Root.set("version", "1.1")
        Root.set("height", str(CellHeight * self.Rows + 1))
        Root.set("width", str(CellWidth * self.Cols + 1))
        Root.set("id", "Map-" + self.Title)

        TileGroup = Etree.SubElement(Root, qname('g'))
        for Coord in self.Tiles:
            TileNode = self.Tiles[Coord].nodeSvg(CellWidth, CellHeight, self.Title)
            TileGroup.append(TileNode)

        OutlineGroup = Etree.SubElement(Root, qname('g'))
        Rect = Etree.SubElement(OutlineGroup, qname("rect"))
        Rect.set('x', '0.5')
        Rect.set('y', '0.5')
        Rect.set("width", str(self.Cols * CellWidth))
        Rect.set("height", str(self.Rows * CellHeight))
        Rect.set("fill", "none")
        Rect.set("stroke", "black")

        for Col in range(1, self.Cols):
            Line = Etree.SubElement(OutlineGroup, qname("line"))
            x = str(Col * CellWidth + 0.5)
            Line.set("x1", x)
            Line.set("y1", '0.5')
            Line.set("x2", x)
            Line.set("y2", str(self.Rows * CellHeight + 0.5))
            Line.set("stroke", "black")

        for Row in range(1, self.Rows):
            Line = Etree.SubElement(OutlineGroup, qname("line"))
            y = str(Row * CellHeight + 0.5)
            Line.set("x1", '0.5')
            Line.set("y1", y)
            Line.set("x2", str(self.Cols * CellWidth + 0.5))
            Line.set("y2", y)
            Line.set("stroke", "black")


        return Root

def genHtml():
    def tableRow(lines, key, value):
        if value is None:
            return

        if key is not None:
            lines.append('<tr><th>{}</th><td>'.format(key))

        if isinstance(value, (list, tuple)):
            lines.append('<ul>')
            for Item in value:
                lines.append('<li>')
                tableRow(lines, None, Item)
                lines.append('</li>')
            lines.append('</ul>')
        else:
            lines.append(str(value))

        if key is not None:
            lines.append('</td></tr>')

    Lines = ["<!DOCTYPE html>",]
    Lines.append('<html lang="en">')
    Lines.append('<head>')
    Lines.append('<title>Hyrule Warriors Map</title>')
    Lines.append('<meta charset="utf-8"/>')
    Lines.append('<style>')
    with open("style.css", 'r') as f:
        Lines.append(f.read())
    Lines.append('</style>')
    Lines.append('</head>')

    Lines.append('<body>')
    Lines.append('<div id="Content">')
    Lines.append('<header>')
    Lines.append('<h1>Hyrule Warriors Adventure Maps</h1>')
    Lines.append('<p id="Attribution">Data extracted from Allen Tyner’s (aka. <a href="https://gamefaqs.gamespot.com/community/SBAllen">SBAllen</a>’s) <a href="https://gamefaqs.gamespot.com/3ds/167257-hyrule-warriors-legends/faqs/73095/">Unlockable Guide</a>.</p>')
    Lines.append('</header>')
    Lines.append('<div id="maps">')

    with open("maps.xml", 'rb') as f:
        Maps = Etree.XML(f.read())

    for MapNode in Maps:
        Map = MapInfo()
        Map.Title = MapNode.get("name")
        for TileNode in MapNode[0]:
            Tile = TileInfo.fromNode(TileNode)
            Map.addTile(Tile)
        if len(Map.Tiles) <= 0:
            continue

        Svg = Map.genSvg()
        Lines.append('<div id="MapWrapper-{}" class="MapWrapper">'.format(Map.Title))
        Lines.append('<h2>{}</h2>'.format(Map.Title + " Map"))
        Lines.append('<div class="SvgWrapper">')
        Lines.append(Etree.tostring(Svg, encoding="utf-8", pretty_print=True,
                                    xml_declaration=False).decode("utf-8"))
        Lines.append('</div>')
        Lines.append('<div class="TilesWrapper">')
        for Coord in Map.Tiles:
            Tile = Map.Tiles[Coord]
            Lines.append('<div id="Tile-{}-{}" class="TileWrapper">'.format(
                Map.Title, Tile.Coord))
            Lines.append('<h3 class="TileTitle">{}</h3>'.format(Tile.Coord))
            Lines.append('<table id="TileData-{}-{}">'.format(Map.Title, Tile.Coord))
            Lines.append('<tbody>')
            tableRow(Lines, "Mission", Tile.Mission)
            tableRow(Lines, "Loot", Tile.LootV)
            tableRow(Lines, "Treasure", Tile.Treasure)
            tableRow(Lines, "A-rank loot", Tile.LootA)
            tableRow(Lines, "A-rank KO", Tile.KoA)
            tableRow(Lines, "A-rank time", Tile.TimeA)
            tableRow(Lines, "A-rank damage", Tile.DamageA)
            Lines.append('</tbody>')
            Lines.append('</table>')
            Lines.append('</div>')

        Lines.append('</div>')
        Lines.append('</div>')

    Lines.append('</div>')
    Lines.append('</div>')
    Lines.append('<script>')
    with open("logic.js", 'r') as f:
        Lines.append(f.read())
    Lines.append('</script>')
    Lines.append('</body>')
    Lines.append('</html>')
    return '\n'.join(Lines)

def main():
    with open("maps.html", 'wb') as f:
        f.write(genHtml().encode("utf-8"))

if __name__ == "__main__":
    main()
