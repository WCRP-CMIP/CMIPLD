function chart(data) {
  // Clear any existing chart
  const chartContainer = document.getElementById('chart');
  chartContainer.innerHTML = '';

  // Specify the chart's dimensions.
  const width = d3.min([window.innerWidth, window.innerHeight]);
  const height = width;

  // Create the color scale.
  const color = d3.scaleOrdinal(d3.schemeCategory10);

  // Compute the layout.
  const pack = (data) =>
    d3.pack().size([width, height]).padding(5)(
      d3
        .hierarchy(data)
        .sum((d) => d.size)
        // .sort((a, b) => b.size - a.size)
    );

    // function d3_layout_packSort(a, b) {
    //   return -(a.value - b.value);
    // }
  const root = pack(data);

  // Create the SVG container.
  const svg = d3
    .create("svg")
    .attr("viewBox", `-${width / 2} -${height / 2} ${width} ${height}`)
    .attr("width", width)
    .attr("height", height)
    .attr('fill', '#555')
    .attr("text-anchor", "middle")

    .attr(
      "style",
      `max-width: 100%; height: auto; display: block; margin: 0 -14px; background: white; cursor: pointer;`
    );


  window.nodes = root.descendants().slice(1)

  function sanitizeUrl(url) {
    return url.toLowerCase().replace(/([^:]\/)\/+/g, '$1');
  }

  window.bundlenodes = {}


  window.nodes.forEach((d) => {

    if (d.data.jsonld) {

      window.bundlenodes[sanitizeUrl(d.data.jsonld)] = d

    }
  })
  window.bundlelinks = []

  links.map((d) => {
    // if (window.bundlenodes[sanitizeUrl(d[0])] && window.bundlenodes[sanitizeUrl(d[1])]) {
    if (window.bundlenodes[sanitizeUrl(d[0])] && window.bundlenodes[sanitizeUrl(d[1])]) {

      window.bundlelinks.push({ "source": sanitizeUrl(d[0]), "target": sanitizeUrl(d[1]) })
    }
    // else {
    //   console.log(d)
    // }
  }

  )

  // console.log(index)

  var fbundling = d3.ForceEdgeBundling()
    .step_size(0.1)
    .compatibility_threshold(0.9)
    .nodes(window.bundlenodes)
    .edges(window.bundlelinks);
  window.results = fbundling();


  // Define the line generator
  var d3line = d3.line()
    .x(function (d) { return d.x; })
    .y(function (d) { return d.y; })
    .curve(d3.curveLinear); // Use curveLinear for "linear" interpolation

  // Iterate over the results and draw lines
  const svglinks = svg.append("g")
    .style("mix-blend-mode", "multiply")
    .style("stroke-width", .5)
    .style("fill", "none")
    .style("stroke-opacity", 0.3)

  results.forEach(function (edge_subpoint_data, i) {
    let lcol = color(edge_subpoint_data[0].data.prefix)
    svglinks.append("path")
      .attr("d", d3line(edge_subpoint_data))
      .style("stroke", lcol)// "#ff2222")


    // Use opacity as blending
  });



function linkstroke(d) {
  return d.depth==2?'none':color(d.data.prefix)
}


const head = d3.select("#title")
  // Append the nodes.
  const node = svg
    .append("g")
    .selectAll("circle")
    .data(window.nodes)
    .join("circle")
    .attr("fill", "white")
    .attr("fill-opacity", 0.1)
    .attr("stroke", linkstroke)
    .attr("stroke-width", (d) => (d.depth == 2 ? 2 : 1))
    .attr("stroke-opacity", (d) => (d.depth ===1? 0.3: d.depth < 3 === 0 ? 1 : 0.4))
    .attr("stroke-dasharray", (d) => (d.depth != 1 ? "0" : "8 6"))
    .attr("pointer-events", (d) => (!d.children ? "none" : null))
    .on("mouseover", function () {
      d3.select(this).attr("stroke", (d) => {
        head.text(`${d.data.prefix} : ${d.data.name}`)
        return color(d.data.prefix)}
    );
      
      
    })
    .on("mouseout", function () {
      d3.select(this)
        .attr("stroke", linkstroke)
        .attr("stroke-opacity", 1);
    })
    .on(
      "click",
    
      (event, d) => focus !== d && (zoom(event, d), event.stopPropagation()) 
    );

  console.log(links)

  // Append the text labels.
  const label = svg
    .append("g")
    .style("font", "10px sans-serif")
    .attr("pointer-events", "none")
    .attr("text-anchor", "middle")

    .selectAll("text")
    .data(root.descendants())
    .join("text")
    .style("fill-opacity", (d) => (d.parent === root ? 1 : 0))
    .style("display", (d) => (d.parent === root ? "inline" : "none"))
    .style("font-size", (d) =>
      d.depth < 2 ? "2.5em" : d.depth > 2 ? "0.01em" : "1em"
    )
    .attr("text-align", "center")
    .attr("backdrop-filter", "blur(10px)")
    // .attr("color", "red")
    .text((d) => d.data.name.toUpperCase());

  // Create the zoom behavior and zoom immediately in to the initial focus node.
  svg.on("click", (event) => zoom(event, root));
  let focus = root;
  let view;
  zoomTo([focus.x, focus.y, focus.r * 2]);

  function zoomTo(v) {
    const k = width / v[2];

    view = v;

    label.attr(
      "transform",
      (d) => `translate(${(d.x - v[0]) * k},${(d.y - v[1]) * k})`
    );
    node.attr(
      "transform",
      (d) => `translate(${(d.x - v[0]) * k},${(d.y - v[1]) * k})`
    );

    console.log(k, v, width / 2)

    svglinks.attr(
      "transform",
      `translate(${-v[0]},${-v[1]})`
    );

    if (Math.floor(k) != 1) {
      svglinks.attr("opacity", 0)
    } else {
      svglinks.attr("opacity", 1)
    }

    node.attr("r", (d) => d.r * k);
  }

  function zoom(event, d) {
    const focus0 = focus;

    focus = d;

    const transition = svg
      .transition()
      .duration(event.altKey ? 7500 : 750)
      .tween("zoom", (d) => {
        const i = d3.interpolateZoom(view, [focus.x, focus.y, focus.r * 2]);
        return (t) => zoomTo(i(t));
      });

    label
      .filter(function (d) {
        return d.parent === focus || this.style.display === "inline";
      })
      .transition(transition)
      .style("fill-opacity", (d) => (d.parent === focus ? 1 : 0))
      .attr("backdrop-filter", "blur(10px)")
      .on("start", function (d) {
        if (d.parent === focus) this.style.display = "inline";
      })
      .on("end", function (d) {
        if (d.parent !== focus) this.style.display = "none";
      });
  }

  // Add the SVG to the chart container
  document.getElementById('chart').appendChild(svg.node());
}

// When the data is loaded, call the chart function
document.addEventListener('DOMContentLoaded', () => {
  // Check if the data is already loaded (via script tag)
  if (window.data) {
    chart(window.data);
  } else {
    // Fetch the data if not already loaded
    fetch('https://wcrp-cmip.github.io/LD-Collection/universe_contents/universe_hierarchy.json')
      .then(response => response.json())
      .then(data => chart(data))
      .catch(error => console.error('Error loading data:', error));
  }
});


// npm install -g nodemon