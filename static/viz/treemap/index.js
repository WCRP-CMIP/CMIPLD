import * as d3 from 'https://cdn.jsdelivr.net/npm/d3@7/+esm';
const url ='https://wcrp-cmip.github.io/LD-Collection/universe_contents/universe_hierarchy.json'



async function createTreemap() {
    // Fetch data
    const response = await fetch(url);
    const data = await response.json();

    // Clear previous chart
    const container = document.getElementById('chart-container');
    container.innerHTML = '';

    // Responsive dimensions
    const containerWidth = container.clientWidth;
    const containerHeight = container.clientHeight;
    
    const width = containerWidth;
    const height = containerHeight;

    // Color generation
    const colours = d3.schemeCategory10.map((d) => 
        d3.scaleSequential([5, 0], (t) => d3.interpolate(d, "white")(t))
    );
    
    const color = {};
    data.children.forEach((d, i) => (color[d.prefix] = colours[i]));

    // Treemap layout
    const treemap = (data) => 
        d3.treemap()
            .size([width, height])
            .paddingOuter(0)
            .paddingTop(19)
            .paddingInner(1)
            .round(true)(
                d3.hierarchy(data)
                    .sum((d) => d.size)
                    .sort((a, b) => b.size - a.size)
            );

    const root = treemap(data);

    // Create SVG
    const svg = d3.select('#chart-container')
        .append('svg')
        .attr('width', width)
        .attr('height', height)
        .attr('viewBox', [0, 0, width, height])
        .style('max-width', '100%')
        .style('height', 'auto')
        .style('overflow', 'visible')
        .style('font', '10px sans-serif');

    // Shadow filter
    const shadow = svg.append('defs')
        .append('filter')
        .attr('id', 'drop-shadow')
        .append('feDropShadow')
            .attr('flood-opacity', 0.3)
            .attr('dx', 0)
            .attr('stdDeviation', 3);

    // Nodes
    const node = svg
        .selectAll('g')
        .data(d3.group(root, (d) => d.height))
        .join('g')
        .attr('filter', 'url(#drop-shadow)')
        .selectAll('g')
        .data((d) => d[1])
        .join('g')
        .attr('transform', (d) => `translate(${d.x0},${d.y0})`);

    const format = d3.format(',d');

    // Title
    node.append('title').text(
        (d) => `${d.ancestors().reverse().map((d) => d.data.name).join('/')}\n${format(d.value)}`
    );

    // Rectangles with unique IDs
    node
        .append('rect')
        .attr('id', (d, i) => `rect-${i}`)
        .attr('fill', (d) => d.depth > 0 ? color[d.data.prefix](d.height) : 'white')
        .attr('width', (d) => d.x1 - d.x0)
        .attr('height', (d) => d.y1 - d.y0);

    // Clip paths
    node
        .append('clipPath')
        .attr('id', (d, i) => `clip-${i}`)
        .append('use')
        .attr('href', (d, i) => `#rect-${i}`);

    // Text with improved positioning
    const text = node
        .append('text')
        .attr('clip-path', (d, i) => `url(#clip-${i})`)
        .selectAll('tspan')
        .data((d) => {
            const nameParts = d.data.name.split(/(?=[A-Z][^A-Z])/g);
            return [...nameParts, d.depth>2?"":format(d.value)];
        })
        .join('tspan')
        .attr('fill-opacity', (d, i, nodes) => 
            i === nodes.length - 1 ? 0.7 : null
        )
        .attr('font-size', (d, i, nodes) =>d.depth>2?"0.2em":'1em')
        .text((d) => d);

    // Positioning for parent nodes (with children)
    node
        .filter((d) => d.children)
        .selectAll('tspan')
        .attr('dx', 3)
        .attr('y', 13);

    // Positioning for leaf nodes (no children)
    node
        .filter((d) => !d.children)
        .selectAll('tspan')
        .attr('x', 3)
        .attr('y', (d, i, nodes) => {
            const isLastItem = i === nodes.length - 1;
            return isLastItem ? '1.4em' : '1em';//`${i * 0.9}em`;
        });

    return svg.node();
}

// Initial render
createTreemap();

// Responsive resize
window.addEventListener('resize', createTreemap);