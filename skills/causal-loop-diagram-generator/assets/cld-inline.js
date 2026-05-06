// Inline CLD renderer — used by the article pages to render multiple CLDs
// directly on the page (no iframes). Each diagram is a <div class="cld-inline"
// data-cld="<id>" data-src="<json url>"></div>.
//
// Why inline instead of iframes: the iframe approach hits a per-document
// rendering ceiling around the 6th instance in both Chrome and Firefox —
// vis-network silently never paints in later iframes. Sharing a single JS
// context makes that limit go away because there is only one document and
// one vis-network library load.

(function () {
    'use strict';

    const VIS_JS = 'https://unpkg.com/vis-network@10.0.1/standalone/umd/vis-network.min.js';

    let visLoading = null;
    function loadVisNetwork() {
        if (window.vis && window.vis.Network) return Promise.resolve();
        if (visLoading) return visLoading;
        visLoading = new Promise(function (resolve, reject) {
            const s = document.createElement('script');
            s.src = VIS_JS;
            s.async = true;
            s.onload = resolve;
            s.onerror = function () { reject(new Error('Failed to load vis-network')); };
            document.head.appendChild(s);
        });
        return visLoading;
    }

    function wrapText(text, maxLen) {
        if (!text || text.length <= maxLen) return text;
        const words = text.split(' ');
        const lines = [];
        let line = '';
        for (let i = 0; i < words.length; i++) {
            const w = words[i];
            if ((line + ' ' + w).trim().length <= maxLen) {
                line = (line ? line + ' ' : '') + w;
            } else {
                if (line) lines.push(line);
                line = w;
            }
        }
        if (line) lines.push(line);
        return lines.join('\n');
    }

    // Custom wheel-zoom: vertical scroll passes through (page scroll), horizontal
    // and pinch zoom the network. Matches the iframe viewer's behavior.
    function attachCustomZoom(container, network) {
        const ZOOM_PER_TICK = 0.04;
        const MIN_SCALE = 0.1;
        const MAX_SCALE = 5.0;
        container.addEventListener('wheel', function (event) {
            if (!network) return;
            const isPinch = event.ctrlKey;
            const dx = event.deltaX, dy = event.deltaY;
            const isHorizontalDominant = Math.abs(dx) > Math.abs(dy) && dx !== 0;
            if (!isPinch && !isHorizontalDominant) return;
            event.preventDefault();
            let delta = isPinch ? dy : dx;
            if (event.deltaMode === 1) delta *= 16;
            else if (event.deltaMode === 2) delta *= 400;
            if (delta === 0) return;
            const direction = delta < 0 ? 1 : -1;
            const magnitude = Math.min(Math.abs(delta), 60) / 60;
            const factor = 1 + direction * ZOOM_PER_TICK * magnitude;
            const oldScale = network.getScale();
            const newScale = Math.max(MIN_SCALE, Math.min(MAX_SCALE, oldScale * factor));
            if (newScale === oldScale) return;
            const rect = container.getBoundingClientRect();
            const pointerDom = { x: event.clientX - rect.left, y: event.clientY - rect.top };
            const pointerCanvas = network.DOMtoCanvas(pointerDom);
            const view = network.getViewPosition();
            const newView = {
                x: pointerCanvas.x - (pointerCanvas.x - view.x) * (oldScale / newScale),
                y: pointerCanvas.y - (pointerCanvas.y - view.y) * (oldScale / newScale)
            };
            network.moveTo({ scale: newScale, position: newView, animation: false });
        }, { passive: false });
    }

    function buildVisNodes(data) {
        const out = data.nodes.map(function (n) {
            return {
                id: n.id,
                label: wrapText(n.label, 18),
                x: n.position.x,
                y: n.position.y,
                title: n.description || n.label
            };
        });
        if (Array.isArray(data.loops)) {
            data.loops.forEach(function (loop) {
                if (!loop.position) return;
                out.push({
                    id: 'loop_' + loop.id,
                    label: loop.type === 'reinforcing' ? 'R' : 'B',
                    x: loop.position.x,
                    y: loop.position.y,
                    shape: 'ellipse',
                    size: 26,
                    color: {
                        background: loop.type === 'reinforcing' ? '#dc3545' : '#28a745',
                        border: '#000'
                    },
                    font: { color: 'white', size: 22, face: 'Arial' },
                    widthConstraint: { minimum: 40, maximum: 40 },
                    heightConstraint: { minimum: 40, valign: 'middle' },
                    title: (loop.label || loop.id) + ': ' + (loop.description || '')
                });
            });
        }
        return out;
    }

    function buildVisEdges(data) {
        return data.edges.map(function (e) {
            return {
                id: e.id,
                from: e.source,
                to: e.target,
                label: e.polarity === 'positive' ? '+' : '−',
                color: { color: e.polarity === 'positive' ? '#28a745' : '#dc3545' },
                title: e.description || '',
                font: {
                    size: 28,
                    color: e.polarity === 'positive' ? '#1e7e34' : '#a71d2a',
                    strokeWidth: 4,
                    strokeColor: 'white',
                    align: 'middle'
                },
                smooth: { type: 'curvedCW', roundness: 0.18 }
            };
        });
    }

    const NETWORK_OPTIONS = {
        layout: { improvedLayout: false },
        physics: { enabled: false },
        interaction: {
            selectConnectedEdges: false,
            zoomView: false,
            dragView: true,
            hover: true,
            tooltipDelay: 200
        },
        nodes: {
            shape: 'box',
            margin: 10,
            font: { size: 16, face: 'Arial' },
            borderWidth: 2,
            shadow: true,
            color: {
                background: 'white',
                border: 'dodgerblue',
                highlight: { background: 'lightskyblue', border: 'darkblue' }
            }
        },
        edges: {
            arrows: { to: { enabled: true, scaleFactor: 1.0 } },
            width: 2,
            smooth: { type: 'curvedCW', roundness: 0.18 }
        }
    };

    async function render(container) {
        if (container.dataset.rendered === '1') return;
        container.dataset.rendered = '1';

        const src = container.dataset.src;
        if (!src) {
            container.innerHTML = '<div style="padding:1em;color:#a71d2a">Missing data-src on .cld-inline element.</div>';
            return;
        }

        try {
            const [data] = await Promise.all([
                fetch(src).then(function (r) {
                    if (!r.ok) throw new Error('Failed to fetch ' + src + ' (' + r.status + ')');
                    return r.json();
                }),
                loadVisNetwork()
            ]);

            const networkDiv = document.createElement('div');
            networkDiv.style.position = 'absolute';
            networkDiv.style.inset = '0';
            container.appendChild(networkDiv);

            const network = new vis.Network(networkDiv, {
                nodes: new vis.DataSet(buildVisNodes(data)),
                edges: new vis.DataSet(buildVisEdges(data))
            }, NETWORK_OPTIONS);

            attachCustomZoom(networkDiv, network);

            // Title overlay
            const overlay = document.createElement('div');
            overlay.className = 'cld-inline-title';
            overlay.textContent = (data.metadata && data.metadata.title) || '';
            container.appendChild(overlay);

            network.fit({ animation: false });

            // Watch for size changes (e.g. responsive layout shifts) and refit.
            if ('ResizeObserver' in window) {
                let lastW = 0, lastH = 0;
                const ro = new ResizeObserver(function (entries) {
                    const r = entries[0].contentRect;
                    if (r.width <= 0 || r.height <= 0) return;
                    if (r.width === lastW && r.height === lastH) return;
                    lastW = r.width; lastH = r.height;
                    network.setSize(r.width + 'px', r.height + 'px');
                    network.redraw();
                });
                ro.observe(networkDiv);
            }
        } catch (err) {
            container.innerHTML = '<div style="padding:1em;color:#a71d2a">Failed to render CLD: ' + err.message + '</div>';
            container.dataset.rendered = '0';
        }
    }

    function init() {
        const containers = document.querySelectorAll('.cld-inline[data-src]');
        if (!containers.length) return;

        if (!('IntersectionObserver' in window)) {
            containers.forEach(render);
            return;
        }

        const io = new IntersectionObserver(function (entries) {
            entries.forEach(function (entry) {
                if (entry.isIntersecting) {
                    io.unobserve(entry.target);
                    render(entry.target);
                }
            });
        }, { rootMargin: '300px 0px', threshold: 0.01 });

        containers.forEach(function (c) { io.observe(c); });
    }

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', init);
    } else {
        init();
    }
})();
