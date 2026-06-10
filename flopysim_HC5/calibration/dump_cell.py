import nbformat
nb = nbformat.read(r"F:\Users\abolmaal\Code\GreatLakesProject\flopysim_HC5\Modeflow6_SImulation.ipynb", as_version=4)
for i, c in enumerate(nb.cells):
    if c.cell_type != "code":
        continue
    s = "".join(c.source)
    first = s.strip().splitlines()[0][:55] if s.strip() else "(empty)"
    print(f"{i:3d} | RUN={'run_simulation' in s} | SS={'sim_ss' in s or 'nameModel_SS' in s} | NAMESIM={'sim_name=nameSim' in s} | {first}")