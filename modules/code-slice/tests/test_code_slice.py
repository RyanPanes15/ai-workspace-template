#!/usr/bin/env python3
"""Fixture tests for cs.py: python modules/code-slice/tests/test_code_slice.py [--fallback]

Copies tests/ws to a temp dir (so `diff` can use a throwaway git repo) and checks each
command's output for the lines it must and must not contain.
"""
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
CS = HERE.parent / "cs.py"

CASES = [
    # (args, must contain, must not contain)
    (["outline", "OrderFrm.cs"], ["L15-25 method btnSave_Click", "L27-31 method SaveOrder"], []),
    (["outline", "order_pkg.sql"], ["procedure INSERT_ORDER", "table ORDERS"], []),
    (["show", "OrderForm.tsx:41", "--max-lines", "15"], [">41|", "lines folded (L26-38)", "handleSubmit"], ["useEffect"]),
    (["show", "validateOrder"], ["validation.ts:3-18", "return errs;"], []),
    (["show", "OrderFrm.cs:19", "--around", "2"], ["納期は受注日以降", "btnSave_Click"], ["InitializeComponent"]),
    (["find", "saveOrder"], ["orderApi.ts:3-6"], []),
    (["refs", "saveOrder"], ["OrderForm.handleSubmit  L41", "saveOrder  L3 (def)"], []),
    (["flow", "OrderForm.tsx#handleSubmit"], ["validateOrder  <- called at", "OrderForm.tsx:41 (import)"], []),
    (["flow", "saveOrder", "--up", "1"], ["-> calls saveOrder (caller)"], []),
    (["trace", "logs/node-trace.txt"], ["saveOrder  [innermost repo frame]", ">5|", "[caller]", "react-dom"], []),
    (["trace", "logs/java-trace.txt"], ["OrderService.save  [innermost repo frame]", ">18|", "OrderController.java:44"], []),
    (["trace", "logs/dotnet-trace.txt"], ["SaveOrder  [innermost repo frame]", ">30|", ">24|"], []),
    (["field", "deliveryDate"], ["## database · sql", "## legacy-frontend", "dtpDeliveryDate", "DELIVERY_DATE"], ["· test"]),
    (["field", "deliveryDate", "--scope", "repos/web/src/screens/order", "--show"],
     ["reference slices", ">54|", ">33|"], ["OrderFrm.cs", "CustomerForm"]),
    (["sql", "INSERT_ORDER"], ["[procedure]", "END INSERT_ORDER;"], ["COUNT_ORDERS"]),
    (["sql", "LOG_IT"], [":37-40  AUDIT_PKG.LOG_IT", "procedure decl"], []),
    (["sql", "--column", "delivery_date"], ["table ORDERS", "COMMENT ON COLUMN"], []),
    (["diff", "web"], ["validateOrder", ">14|", "untracked (not in the diff): src/api/untracked.ts"], ["CustomerForm"]),
    (["json", "big.json", "--find", "delivery"], ["components.schemas.Order.properties.deliveryDate"], []),
    (["outline", "langs/a.kt", "langs/a.vb", "langs/a.go", "langs/a.py", "langs/a.php"],
     ["L2-7 function save", "L7-9 method Save", "L12-14 method M", "L2-5 function m", "L3-6 method save"], [], "ts"),
]


def main():
    fallback = "--fallback" in sys.argv
    tmp = Path(tempfile.mkdtemp(prefix="cs-test-"))
    ws = tmp / "ws"
    shutil.copytree(HERE / "ws", ws)
    web = ws / "repos" / "web"
    git = ["git", "-C", str(web), "-c", "user.email=t@t", "-c", "user.name=t", "-c", "safe.directory=*"]
    subprocess.run(git + ["init", "-q"], check=True)
    subprocess.run(git + ["add", "-A"], check=True)
    subprocess.run(git + ["commit", "-qm", "init"], check=True)
    v = web / "src/screens/order/validation.ts"
    v.write_text(v.read_text().replace("    errs.push('qty must be positive');\n  }",
                                       "    errs.push('qty must be positive');\n  }\n  if (o.qty > 9999) {\n"
                                       "    errs.push('qty too large');\n  }"))
    (web / "src/api/untracked.ts").write_text("export const y = 2;\n")
    (ws / "big.json").write_text('{"components":{"schemas":{"Order":{"properties":{"deliveryDate":{"type":"string"}}}}}}')
    env = dict(os.environ, CODE_SLICE_ROOT=str(ws), GIT_CONFIG_COUNT="1", GIT_CONFIG_KEY_0="safe.directory",
               GIT_CONFIG_VALUE_0="*")
    if fallback:
        env["CODE_SLICE_FALLBACK"] = "1"
    fails = ran = 0
    for args, must, must_not, *flags in CASES:
        if fallback and "ts" in flags:
            continue
        ran += 1
        r = subprocess.run([sys.executable, str(CS)] + args, cwd=ws, env=env, capture_output=True, text=True,
                           encoding="utf-8")
        out = r.stdout + r.stderr
        missing = [m for m in must if m not in out]
        extra = [m for m in must_not if m in out]
        ok = not missing and not extra and "Traceback" not in out
        fails += not ok
        print(f"{'ok  ' if ok else 'FAIL'} {' '.join(args)}")
        if not ok:
            for m in missing:
                print(f"     missing: {m!r}")
            for m in extra:
                print(f"     unexpected: {m!r}")
            if "Traceback" in out:
                print("     " + out[-600:].replace("\n", "\n     "))
    shutil.rmtree(tmp, ignore_errors=True)
    print(f"-- {ran - fails}/{ran} passed" + (" (fallback mode)" if fallback else ""))
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
