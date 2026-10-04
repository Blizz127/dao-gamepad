// Decompile the functions at the given entry addresses into one C file.
// Args: OUT_PATH ADDR [ADDR ...]   (addresses in hex, e.g. 00882680)
//@category DAO

import ghidra.app.decompiler.DecompInterface;
import ghidra.app.decompiler.DecompileResults;
import ghidra.app.script.GhidraScript;
import ghidra.program.model.listing.Function;

import java.io.PrintWriter;

public class DecompileFunctions extends GhidraScript {
    @Override
    public void run() throws Exception {
        String[] args = getScriptArgs();
        if (args.length < 2) {
            printerr("usage: DecompileFunctions.java OUT_PATH ADDR [ADDR ...]");
            return;
        }
        DecompInterface ifc = new DecompInterface();
        ifc.openProgram(currentProgram);
        try (PrintWriter out = new PrintWriter(args[0])) {
            java.util.List<Function> targets = new java.util.ArrayList<>();
            for (int i = 1; i < args.length; i++) {
                if (args[i].contains("-")) {
                    // START-END: every function whose entry lies in [START, END)
                    String[] se = args[i].split("-");
                    ghidra.program.model.address.AddressSet set =
                        new ghidra.program.model.address.AddressSet(toAddr(se[0]), toAddr(se[1]).subtract(1));
                    for (Function f : currentProgram.getFunctionManager().getFunctions(set, true)) {
                        targets.add(f);
                    }
                    continue;
                }
                Function f = getFunctionAt(toAddr(args[i]));
                if (f == null) {
                    f = getFunctionContaining(toAddr(args[i]));
                }
                if (f == null) {
                    out.printf("// %s: no function%n%n", args[i]);
                    continue;
                }
                targets.add(f);
            }
            for (Function f : targets) {
                DecompileResults r = ifc.decompileFunction(f, 120, monitor);
                out.printf("// ===== %s @ %s =====%n", f.getName(), f.getEntryPoint());
                out.println(r.decompileCompleted() ? r.getDecompiledFunction().getC() : "// decompile failed: " + r.getErrorMessage());
                out.println();
            }
        }
        ifc.dispose();
        println("wrote " + args[0]);
    }
}
