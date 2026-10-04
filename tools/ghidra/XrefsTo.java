// List references to the given addresses or external symbol names.
// Args: OUT_PATH TARGET [TARGET ...]   TARGET = hex address or symbol name (e.g. DirectInput8Create)
// Output TSV: target, ref_from, ref_type, function, function_entry
//@category DAO

import ghidra.app.script.GhidraScript;
import ghidra.program.model.address.Address;
import ghidra.program.model.listing.Function;
import ghidra.program.model.symbol.Reference;
import ghidra.program.model.symbol.Symbol;

import java.io.PrintWriter;
import java.util.ArrayList;
import java.util.List;

public class XrefsTo extends GhidraScript {
    @Override
    public void run() throws Exception {
        String[] args = getScriptArgs();
        try (PrintWriter out = new PrintWriter(args[0])) {
            out.println("target\tref_from\tref_type\tfunction\tfunction_entry");
            for (int i = 1; i < args.length; i++) {
                for (Address a : resolve(args[i])) {
                    for (Reference r : getReferencesTo(a)) {
                        Function f = getFunctionContaining(r.getFromAddress());
                        out.printf("%s\t%s\t%s\t%s\t%s%n", args[i], r.getFromAddress(), r.getReferenceType(),
                            f == null ? "-" : f.getName(), f == null ? "-" : f.getEntryPoint());
                    }
                }
            }
        }
        println("wrote " + args[0]);
    }

    private List<Address> resolve(String target) {
        List<Address> out = new ArrayList<>();
        if (target.matches("(0x)?[0-9a-fA-F]{6,}")) {
            out.add(toAddr(target.replaceFirst("^0x", "")));
            return out;
        }
        for (Symbol s : currentProgram.getSymbolTable().getSymbols(target)) {
            out.add(s.getAddress());
            // Imports: also include the IAT thunk/pointer references.
            for (Reference r : getReferencesTo(s.getAddress())) {
                if (r.getReferenceType().isData()) {
                    out.add(r.getFromAddress());
                }
            }
        }
        return out;
    }
}
