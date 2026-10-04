// Dump code references to input-related strings (Gamepad::*, radial/analog names).
// Output: one line per (string, referencing function) to the file named by the first script arg.
//@category DAO

import ghidra.app.script.GhidraScript;
import ghidra.program.model.address.Address;
import ghidra.program.model.listing.Data;
import ghidra.program.model.listing.DataIterator;
import ghidra.program.model.listing.Function;
import ghidra.program.model.symbol.Reference;

import java.io.PrintWriter;
import java.util.regex.Pattern;

public class DumpInputXrefs extends GhidraScript {
    private static final Pattern WANTED = Pattern.compile(
        "^(Gamepad::.*|Mouse::.*|.*Thumbstick.*|.*Radial.*|.*AnalogTarget.*|AnalogScrollValue|radial)$");

    @Override
    public void run() throws Exception {
        String outPath = getScriptArgs().length > 0 ? getScriptArgs()[0] : "input-xrefs.tsv";
        try (PrintWriter out = new PrintWriter(outPath)) {
            out.println("string\tstring_addr\tref_from\tfunction\tfunction_entry");
            DataIterator it = currentProgram.getListing().getDefinedData(true);
            while (it.hasNext() && !monitor.isCancelled()) {
                Data d = it.next();
                if (!d.hasStringValue()) {
                    continue;
                }
                String s = String.valueOf(d.getValue());
                if (!WANTED.matcher(s).matches()) {
                    continue;
                }
                Reference[] refs = getReferencesTo(d.getAddress());
                if (refs.length == 0) {
                    out.printf("%s\t%s\t-\t-\t-%n", s, d.getAddress());
                }
                for (Reference r : refs) {
                    Address from = r.getFromAddress();
                    Function f = getFunctionContaining(from);
                    out.printf("%s\t%s\t%s\t%s\t%s%n", s, d.getAddress(), from,
                        f == null ? "-" : f.getName(), f == null ? "-" : f.getEntryPoint());
                }
            }
        }
        println("wrote " + outPath);
    }
}
