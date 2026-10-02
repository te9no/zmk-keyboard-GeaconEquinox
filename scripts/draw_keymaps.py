#!/usr/bin/env python3
"""Draw both physical layouts using the shared zmk-workspace SVG renderer."""
import argparse
from pathlib import Path
import re
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--tools-dir', type=Path, required=True,
                        help='scripts directory from the pinned zmk-workspace checkout')
    parser.add_argument('--check', action='store_true', help='Fail if checked-in diagrams are stale')
    args = parser.parse_args()
    sys.path.insert(0, str(args.tools_dir.resolve()))
    import generate_physical_layout_svg as svg
    from devicetree_blocks import iter_blocks

    def binding(group):
        aliases = {
            'dial_enter': svg.Binding('ENTER', 'DIAL MENU'),
            'dial_open': svg.Binding('DIAL', 'MENU'),
            'dial_select': svg.Binding('SELECT', 'EXIT'),
            'dial_cancel': svg.Binding('EXIT', 'DIAL'),
            'tog_ls': svg.Binding('US/JIS', 'SHIFT'),
        }
        name = group[0].lstrip('&')
        if name in aliases:
            return aliases[name]
        return svg.format_binding(group)

    stale = []
    with tempfile.TemporaryDirectory() as temp:
        for variant in ('US', 'JIS'):
            source = ROOT / 'config' / f'GeaconEquinox_{variant}.keymap'
            layout = ROOT / 'snippets' / f'equinox-{variant.lower()}' / f'equinox-{variant.lower()}.overlay'
            # Physical keys live in this overlay; firmware includes need not be expanded.
            text = layout.read_text()
            block = svg.find_labeled_block(text, f'layout_{variant}')
            keys = svg.parse_key_attrs(block)
            layers = []
            for _, node in iter_blocks(source.read_text(), re.compile(r'\b(keymap)\s*\{')):
                for name, body in svg.iter_child_blocks(node):
                    match = re.search(r'\bbindings\s*=\s*<(.*?)>;', body, re.S)
                    if not match:
                        continue
                    label = re.search(r'\bdisplay-name\s*=\s*"([^"]+)"', body)
                    bindings = [binding(group) for group in svg.parse_binding_groups(match[1])]
                    if len(bindings) != len(keys):
                        raise SystemExit(f'{variant}/{name}: {len(bindings)} bindings for {len(keys)} keys')
                    layers.append(svg.Layer(name, label[1] if label else name, bindings))
            if not layers:
                raise SystemExit(f'No layers in {source}')
            for suffix, selected in (('', layers), ('-base', layers[:1])):
                filename = f'GeaconEquinox_{variant}{suffix}.svg'
                target = ROOT / 'keymap-svg' / filename
                output = Path(temp) / filename if args.check else target
                svg.render_svg(keys, svg.parse_modules(text), [], f'GeaconEquinox · {variant}',
                               output, 52, 30, False, selected)
                # Explicit background also works in image renderers that ignore SVG CSS backgrounds.
                drawing = output.read_text()
                drawing = drawing.replace('</style>', '</style>\n<rect width="100%" height="100%" fill="#f8faf7"/>', 1)
                output.write_text(drawing)
                if args.check and (not target.exists() or target.read_bytes() != output.read_bytes()):
                    stale.append(filename)
            print(f'{variant}: {len(keys)} keys, {len(layers)} layers')
    if stale:
        raise SystemExit('Stale diagrams: ' + ', '.join(stale))


if __name__ == '__main__':
    main()
