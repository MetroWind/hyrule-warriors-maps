// String formatting
if (!String.prototype.format) {
  String.prototype.format = function() {
    var args = arguments;
    return this.replace(/{(\d+)}/g, function(match, number) {
      return typeof args[number] != 'undefined'
        ? args[number]
        : match
      ;
    });
  };
}

function addHoverListener(btn, bg, text, tile)
{
    btn.addEventListener("mouseover", function(event){
        if(!btn.MapSvg.Selected)
        {
            bg.setAttribute("fill-opacity", "0");
            text.setAttribute("fill", bg.getAttribute("fill"));
            text.setAttribute("font-weight", "bold");
            tile.style.display = "block";
        }
    });
    btn.addEventListener("mouseout", function(event){
        if(!btn.MapSvg.Selected)
        {
            bg.setAttribute("fill-opacity", "1");
            text.setAttribute("fill", "white");
            text.setAttribute("font-weight", "normal");
            tile.style.display = "none";
        }
    });
}


let MapWrappers = document.querySelectorAll(".MapWrapper");
MapWrappers.forEach(function(map_wrapper, i, wrappers) {
    let Match = map_wrapper.getAttribute("id").match(/MapWrapper-(.*)/);
    let MapName = Match[1];
    let MapSvg = document.getElementById("Map-" + MapName);
    let Tiles = map_wrapper.querySelectorAll(".TileWrapper");
    MapSvg.Selected = null;

    Tiles.forEach(function(tile, i, tiles){
        let Match = tile.getAttribute("id").match(/Tile-.*-(.*)/);
        let Coord = Match[1];
        let SvgButton = document.getElementById(
            "TileBtn-{0}-{1}".format(MapName, Coord));
        SvgButton.MapSvg = MapSvg;

        let SvgGroup = SvgButton.parentElement;
        let SvgBg = SvgGroup.querySelector("rect.TileBG");
        let SvgText = SvgGroup.querySelector("text.TileText");
        addHoverListener(SvgButton, SvgBg, SvgText, tile);

        SvgButton.addEventListener("click", function(event){
            if(SvgButton.MapSvg.Selected == null)
            {
                SvgButton.MapSvg.Selected = tile;
                SvgButton.MapSvg.SelectedSvgGroup = SvgGroup;
            }
            else if(SvgButton.MapSvg.Selected != tile)
            {
                SvgButton.MapSvg.Selected.style.display = "none";
                tile.style.display = "block";
                let SelectedSvgBg = SvgButton.MapSvg.SelectedSvgGroup
                    .querySelector("rect.TileBG");
                let SelectedSvgText = SvgButton.MapSvg.SelectedSvgGroup
                    .querySelector("text.TileText");
                SelectedSvgBg.setAttribute("fill-opacity", "1");
                SelectedSvgText.setAttribute("fill", "white");
                SelectedSvgText.setAttribute("font-weight", "normal");

                SvgButton.MapSvg.Selected = tile;
                SvgButton.MapSvg.SelectedSvgGroup = SvgGroup;
                SvgBg.setAttribute("fill-opacity", "0");
                SvgText.setAttribute("fill", SvgBg.getAttribute("fill"));
                SvgText.setAttribute("font-weight", "bold");

            }
            else
            {
                SvgButton.MapSvg.Selected = null;
                SvgButton.MapSvg.SelectedSvgGroup = null;
            }
        });
    })
});
