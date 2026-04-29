import json, uuid

nb_path = r"D:\Users\abolmaal\code\Projects\GreatLakesProject\flopysim\Modeflow6_SImulation.ipynb"

with open(nb_path, encoding="utf-8") as f:
    nb = json.load(f)

print(f"Loaded notebook: {len(nb['cells'])} cells")

# ---------------------------------------------------------------------------
# 1. Build the SS spin-up cell source
# ---------------------------------------------------------------------------
ss_lines = [
    "# ── STEADY-STATE SPIN-UP ─────────────────────────────────────────────────────\n",
    "# Build a separate single-period SS model with annual-average stresses.\n",
    "# The converged head field becomes STRT (initial condition) for the transient\n",
    "# run — far better than starting from raw DEM-based heads.\n",
    "# Output: variable `ss_heads`  shape (nlay, nrow, ncol)\n",
    "# ─────────────────────────────────────────────────────────────────────────────\n",
    "\n",
    "sim_ws_ss = str(Path(MODEL_BASE_DIR) / nameModel_SS)\n",
    "\n",
    "# Clean any previous SS run directory\n",
    "for _v in [\"cbc_ss\", \"hds_ss\"]:\n",
    "    _obj = globals().get(_v, None)\n",
    "    try:\n",
    "        if _obj is not None and hasattr(_obj, \"close\"):\n",
    "            _obj.close()\n",
    "    except Exception:\n",
    "        pass\n",
    "if os.path.isdir(sim_ws_ss):\n",
    "    safe_rmtree(sim_ws_ss)\n",
    "os.makedirs(sim_ws_ss, exist_ok=True)\n",
    "\n",
    "# ── Build SS simulation ───────────────────────────────────────────────────────\n",
    "sim_ss = flopy.mf6.MFSimulation(\n",
    "    sim_name=f\"{nameSim}_SS\", sim_ws=sim_ws_ss, exe_name=exe_path\n",
    ")\n",
    "\n",
    "# Single period — period length is irrelevant for a steady-state solve\n",
    "flopy.mf6.ModflowTdis(\n",
    "    sim_ss, time_units=\"DAYS\", nper=1, perioddata=[(1.0, 1, 1.0)]\n",
    ")\n",
    "\n",
    "ims_ss = flopy.mf6.ModflowIms(\n",
    "    sim_ss,\n",
    "    pname=\"ims_ss\",\n",
    "    complexity=\"MODERATE\",\n",
    "    outer_maximum=500,\n",
    "    inner_maximum=300,\n",
    "    outer_dvclose=1e-3,\n",
    "    inner_dvclose=1e-3,\n",
    "    rcloserecord=1e-3,\n",
    "    linear_acceleration=\"BICGSTAB\",\n",
    "    under_relaxation=\"DBD\",\n",
    "    under_relaxation_theta=0.9,\n",
    "    under_relaxation_kappa=0.0001,\n",
    "    under_relaxation_gamma=0.0,\n",
    "    print_option=\"SUMMARY\",\n",
    "    filename=f\"{nameModel_SS}.ims\",\n",
    ")\n",
    "\n",
    "gwf_ss = flopy.mf6.ModflowGwf(sim_ss, modelname=nameModel_SS, save_flows=True)\n",
    "sim_ss.register_ims_package(ims_ss, [gwf_ss.name])\n",
    "\n",
    "# Same grid geometry as the transient model\n",
    "_icelltype_ss = [1] + [0] * (nlay - 1)\n",
    "\n",
    "flopy.mf6.ModflowGwfdis(\n",
    "    gwf_ss,\n",
    "    nlay=nlay, nrow=nrow, ncol=ncol,\n",
    "    delr=delr, delc=delc,\n",
    "    top=top2d, botm=botm3d, idomain=idomain,\n",
    "    xorigin=xorigin, yorigin=yorigin,\n",
    ")\n",
    "flopy.mf6.ModflowGwfnpf(\n",
    "    gwf_ss,\n",
    "    icelltype=_icelltype_ss, k=hk3d, k33=k33_3d,\n",
    "    save_specific_discharge=True,\n",
    ")\n",
    "\n",
    "# Use existing warm/raw heads as first-guess for the SS solver\n",
    "flopy.mf6.ModflowGwfic(gwf_ss, strt=strt)\n",
    "\n",
    "# Steady state: storage terms are switched off for period 0\n",
    "flopy.mf6.ModflowGwfsto(\n",
    "    gwf_ss, ss=1e-6, sy=0.1, steady_state={0: True}\n",
    ")\n",
    "\n",
    "# Save final heads and budget\n",
    "flopy.mf6.ModflowGwfoc(\n",
    "    gwf_ss,\n",
    "    head_filerecord=f\"{nameModel_SS}.hds\",\n",
    "    budget_filerecord=f\"{nameModel_SS}.cbb\",\n",
    "    saverecord=[(\"HEAD\", \"LAST\"), (\"BUDGET\", \"LAST\")],\n",
    "    printrecord=[(\"HEAD\", \"LAST\"), (\"BUDGET\", \"LAST\")],\n",
    ")\n",
    "\n",
    "# Annual-average recharge: mean over all transient stress periods\n",
    "_rch_stack = np.stack(list(rch_spd.values()), axis=0)   # (nper, nrow, ncol)\n",
    "_rch_avg   = np.mean(_rch_stack, axis=0)\n",
    "flopy.mf6.ModflowGwfrcha(\n",
    "    gwf_ss,\n",
    "    pname=\"RCHA\", filename=f\"{nameModel_SS}.rcha\",\n",
    "    recharge={0: _rch_avg},\n",
    ")\n",
    "print(f\"SS recharge: annual mean = {_rch_avg[_rch_avg > 0].mean()*1000:.2f} mm/day\")\n",
    "\n",
    "# Annual-average GHB: mean stage per cell position across all transient months\n",
    "if USE_GHB and \"ghb_spd\" in globals() and ghb_spd:\n",
    "    from collections import defaultdict\n",
    "    _cell_stages = defaultdict(list)\n",
    "    _cell_cond   = {}\n",
    "    _cell_name   = {}\n",
    "    for _per, _recs in ghb_spd.items():\n",
    "        for _rec in _recs:\n",
    "            _cid = tuple(_rec[0])\n",
    "            _cell_stages[_cid].append(float(_rec[1]))\n",
    "            _cell_cond[_cid] = _rec[2]\n",
    "            if len(_rec) > 3:\n",
    "                _cell_name[_cid] = _rec[3]\n",
    "    _ghb_ss = []\n",
    "    for _cid, _stages in _cell_stages.items():\n",
    "        _entry = [_cid, float(np.mean(_stages)), _cell_cond[_cid]]\n",
    "        if _cid in _cell_name:\n",
    "            _entry.append(_cell_name[_cid])\n",
    "        _ghb_ss.append(_entry)\n",
    "    flopy.mf6.ModflowGwfghb(\n",
    "        gwf_ss,\n",
    "        pname=\"GHB_gl\", filename=f\"{nameModel_SS}.ghb\",\n",
    "        boundnames=True, save_flows=True,\n",
    "        maxbound=len(_ghb_ss),\n",
    "        stress_period_data={0: _ghb_ss},\n",
    "    )\n",
    "    print(f\"SS GHB: {len(_ghb_ss):,} cells with annual-average stages\")\n",
    "\n",
    "# Same drain cells (topography-driven, time-invariant)\n",
    "if USE_DRN and len(drn_rec) > 0:\n",
    "    flopy.mf6.ModflowGwfdrn(\n",
    "        gwf_ss,\n",
    "        pname=\"DRN\", filename=f\"{nameModel_SS}.drn\",\n",
    "        maxbound=len(drn_rec),\n",
    "        stress_period_data={0: drn_rec},\n",
    "        save_flows=True,\n",
    "    )\n",
    "    print(f\"SS DRN: {len(drn_rec):,} cells\")\n",
    "\n",
    "# ── Run SS model ──────────────────────────────────────────────────────────────\n",
    "print(\"\\nWriting and running steady-state spin-up model ...\")\n",
    "sim_ss.write_simulation()\n",
    "success_ss, _ = sim_ss.run_simulation()\n",
    "print(\"SS run success:\", success_ss)\n",
    "if not success_ss:\n",
    "    with open(os.path.join(sim_ws_ss, f\"{nameModel_SS}.lst\")) as _f:\n",
    "        print(\"\".join(_f.readlines()[-60:]))\n",
    "\n",
    "# ── Read SS heads → ss_heads (used as STRT in the transient model below) ──────\n",
    "if success_ss:\n",
    "    _ss_hds_path = os.path.join(sim_ws_ss, f\"{nameModel_SS}.hds\")\n",
    "    _hds_ss      = bf.HeadFile(_ss_hds_path)\n",
    "    ss_heads     = _hds_ss.get_data(kstpkper=(0, 0))   # shape: (nlay, nrow, ncol)\n",
    "\n",
    "    _valid_ss = ss_heads[ss_heads > -1e20]\n",
    "    print(f\"\\nSS heads range: {_valid_ss.min():.1f} – {_valid_ss.max():.1f} m\")\n",
    "    print(f\"SS heads shape: {ss_heads.shape}\")\n",
    "\n",
    "    # Verification map: layers 1, 4, 8\n",
    "    fig, _axes = plt.subplots(1, 3, figsize=(18, 5))\n",
    "    for _ax, _lay in zip(_axes, [0, 3, 7]):\n",
    "        _h = ss_heads[_lay].copy().astype(float)\n",
    "        _h[_h < -1e20] = np.nan\n",
    "        _im = _ax.imshow(_h, cmap=\"viridis\", origin=\"upper\")\n",
    "        plt.colorbar(_im, ax=_ax, label=\"Head (m)\")\n",
    "        _ax.set_title(f\"SS Head — Layer {_lay + 1}\")\n",
    "    plt.suptitle(\"Steady-state spin-up result (used as STRT for transient run)\", fontsize=12)\n",
    "    plt.tight_layout()\n",
    "    plt.show()\n",
    "    print(\"\\u2705 ss_heads ready \\u2014 transient IC will use these converged heads\")\n",
    "else:\n",
    "    raise RuntimeError(\"Steady-state run failed \\u2014 check the .lst file before continuing\")\n",
]

new_cell = {
    "cell_type": "code",
    "execution_count": None,
    "id": uuid.uuid4().hex[:8],
    "metadata": {},
    "outputs": [],
    "source": ss_lines,
}

# ---------------------------------------------------------------------------
# 2. Insert after warmstart cell (f1516b77)
# ---------------------------------------------------------------------------
insert_after_id = "f1516b77"
insert_idx = next(i for i, c in enumerate(nb["cells"]) if c["id"] == insert_after_id)
nb["cells"].insert(insert_idx + 1, new_cell)
print(f"Inserted SS cell at index {insert_idx + 1}  (new id: {new_cell['id']})")

# ---------------------------------------------------------------------------
# 3. Change strt=strt → strt=ss_heads in the transient model build cell
# ---------------------------------------------------------------------------
model_cell_id = "c526a86b"
model_cell = next(c for c in nb["cells"] if c["id"] == model_cell_id)
old_src = "".join(model_cell["source"])

old_ic = "ic = flopy.mf6.ModflowGwfic(gwf, strt=strt)"
new_ic = "ic = flopy.mf6.ModflowGwfic(gwf, strt=ss_heads)  # SS spin-up heads as initial condition"

if old_ic in old_src:
    new_src = old_src.replace(old_ic, new_ic, 1)
    model_cell["source"] = new_src.splitlines(keepends=True)
    print("Updated IC line: strt=strt -> strt=ss_heads")
else:
    # Try to find what is there
    idx = old_src.find("ModflowGwfic")
    print(f"WARNING: exact IC line not found. Context: {repr(old_src[idx:idx+100])}")

# ---------------------------------------------------------------------------
# 4. Save
# ---------------------------------------------------------------------------
with open(nb_path, "w", encoding="utf-8") as f:
    json.dump(nb, f, ensure_ascii=False, indent=1)

print(f"Notebook saved. Total cells: {len(nb['cells'])}")
