// Tiny page runtime for the Old Man Sports Club site.
// Each page's template is a function that returns HTML. This file renders it,
// patches the page in place when something changes (sliders, the photo viewer),
// and wires up clicks and element hooks. No outside libraries needed.

function esc(x) {
  if (x === undefined || x === null || x === false) return '';
  return String(x).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');
}

export class DCLogic {
  constructor(props) { this.props = props || {}; this.state = this.state || {}; }
  setState(patch) {
    var next = typeof patch === 'function' ? patch(this.state, this.props) : patch;
    this.state = Object.assign({}, this.state, next);
    if (this.__update) this.__update();
  }
}

function morph(a, b) {
  if (a.nodeType !== b.nodeType || a.nodeName !== b.nodeName) {
    a.parentNode.replaceChild(b.cloneNode(true), a);
    return;
  }
  if (a.nodeType === 3 || a.nodeType === 8) {
    if (a.nodeValue !== b.nodeValue) a.nodeValue = b.nodeValue;
    return;
  }
  if (a.nodeType !== 1) return;
  var i, at;
  for (i = a.attributes.length - 1; i >= 0; i--) {
    at = a.attributes[i];
    if (!b.hasAttribute(at.name)) a.removeAttribute(at.name);
  }
  for (i = 0; i < b.attributes.length; i++) {
    at = b.attributes[i];
    if (a.getAttribute(at.name) !== at.value) a.setAttribute(at.name, at.value);
  }
  var ac = Array.prototype.slice.call(a.childNodes);
  var bc = Array.prototype.slice.call(b.childNodes);
  for (i = 0; i < bc.length; i++) {
    if (i < ac.length) morph(ac[i], bc[i]);
    else a.appendChild(bc[i].cloneNode(true));
  }
  for (i = bc.length; i < ac.length; i++) ac[i].parentNode.removeChild(ac[i]);
}

export function renderToString(Comp, T, props) {
  var inst = new Comp(props);
  var n = 0;
  return T(inst.renderVals(), function () { return n++; }, esc);
}

export function mount(Comp, T, props, root) {
  var inst = new Comp(props);
  var handlers = [];
  var queued = false;
  function reg(fn) { handlers.push(fn); return handlers.length - 1; }
  function render() {
    queued = false;
    handlers = [];
    var html = T(inst.renderVals(), reg, esc);
    var tpl = document.createElement('template');
    tpl.innerHTML = html;
    var holder = document.createElement('div');
    holder.appendChild(tpl.content);
    morph(root, (function () { var r = root.cloneNode(false); while (holder.firstChild) r.appendChild(holder.firstChild); return r; })());
    var refs = root.querySelectorAll('[data-dc-ref]');
    for (var i = 0; i < refs.length; i++) {
      var fn = handlers[+refs[i].getAttribute('data-dc-ref')];
      if (typeof fn === 'function') fn(refs[i]);
    }
  }
  inst.__update = function () {
    if (queued) return;
    queued = true;
    (window.requestAnimationFrame || setTimeout)(render);
  };
  function call(el, kind, e) {
    var fn = handlers[+el.getAttribute('data-dc-' + kind)];
    if (typeof fn === 'function') fn(e);
  }
  root.addEventListener('click', function (e) {
    var el = e.target.closest('[data-dc-click]');
    if (el && root.contains(el)) call(el, 'click', e);
  });
  root.addEventListener('mouseover', function (e) {
    var el = e.target.closest('[data-dc-mouseenter]');
    if (el && !(e.relatedTarget && el.contains(e.relatedTarget))) call(el, 'mouseenter', e);
  });
  root.addEventListener('mouseout', function (e) {
    var el = e.target.closest('[data-dc-mouseleave]');
    if (el && !(e.relatedTarget && el.contains(e.relatedTarget))) call(el, 'mouseleave', e);
  });
  render();
  if (typeof inst.componentDidMount === 'function') inst.componentDidMount();
  return inst;
}
