"""Run in a clean installed environment, outside the checkout, without JS tools."""

import importlib.metadata
import json
import os
import shutil
import socket
import sys
import xml.etree.ElementTree as ET
from concurrent.futures import ThreadPoolExecutor
from importlib import resources
from pathlib import Path


def deny_external_access(event, args):
    if event.startswith("socket.") or event in {
        "subprocess.Popen",
        "os.system",
        "os.posix_spawn",
        "os.spawn",
    }:
        raise RuntimeError(f"External access is disabled in acceptance checks: {event}")


def main():
    # Imports above do not import the wrapper. Guard installation's first import
    # as well as rendering. No JS networking/Node host APIs are ever registered.
    if os.environ.get("PELE_ACCEPTANCE_OS_NETWORK_BLOCKED") == "1":
        try:
            with socket.socket() as connection:
                connection.connect(("127.0.0.1", 9))
        except PermissionError:
            print("PASS: operating-system sandbox denies network access")
        else:
            raise AssertionError("OS network sandbox did not deny the connection")
    os.environ["PATH"] = ""
    assert shutil.which("node") is None and shutil.which("npm") is None
    sys.addaudithook(deny_external_access)
    try:
        socket.socket()
    except RuntimeError as error:
        assert "External access is disabled" in str(error)
    else:
        raise AssertionError("Network guard did not activate")

    import pele_python
    from pele_python import PeleError, render, render_svg

    installed_path = Path(pele_python.__file__).resolve()
    assert "site-packages" in installed_path.parts, installed_path
    assert "IPython" not in sys.modules
    assert importlib.metadata.version("quickjs-ng") == "0.17.0.2"
    vendor = resources.files(pele_python).joinpath("_vendor")
    assert vendor.joinpath("LICENSE").read_text("utf-8").startswith("MIT License")
    assert json.loads(vendor.joinpath("manifest.json").read_text("utf-8"))["name"] == "pele"

    diagrams = json.loads(Path(sys.argv[1]).read_text("utf-8"))
    for kind, fixture in diagrams.items():
        svg = render_svg(fixture["source"], idPrefix=kind, now=1767225600000)
        root = ET.fromstring(svg)
        assert root.tag == "{http://www.w3.org/2000/svg}svg"
        text = "".join(root.itertext())
        assert all(label in text for label in fixture["labels"])

    source = "flowchart LR\n accTitle: Separate IDs\n A[Input] --> B[Output]"
    with ThreadPoolExecutor(max_workers=4) as pool:
        outputs = list(pool.map(lambda _: render_svg(source), range(8)))
    ids = [ET.fromstring(svg).attrib["aria-labelledby"] for svg in outputs]
    assert len(set(ids)) == 8
    diagram = render(source)
    assert diagram._repr_svg_() is diagram.svg
    try:
        render_svg("flowchart LR\n A[unterminated")
    except PeleError as error:
        assert error.code == "syntax" and error.line == 2
    else:
        raise AssertionError("Expected a syntax diagnostic")
    assert render_svg(source).startswith("<svg")
    assert "IPython" not in sys.modules
    print(f"PASS: installed wheel, six types, threads, errors, notebook protocol: {installed_path}")
    print("PASS: empty PATH and blocked Python network/subprocess APIs during import and render")


if __name__ == "__main__":
    main()
