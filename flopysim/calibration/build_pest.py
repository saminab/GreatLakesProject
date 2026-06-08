"""
build_pest.py  --  Assemble the PEST++ control file (calib.pst) with pyEMU.

Run AFTER make_obs.py has produced obs_wells.csv.  It:
  1. writes pest_params.dat.tpl   (template -> pest_params.dat)
  2. writes sim_heads.dat.ins     (instruction -> reads sim_heads.dat)
  3. builds calib.pst with parameter bounds/transforms and observation
     values + weights (one head observation per target well, grouped by layer)
  4. sets the model command to run_forward.bat and PEST++ options.

Engine: pestpp-glm (gradient/regularised Gauss-Levenberg-Marquardt) is the
recommended driver for 5 parameters.  Each GLM iteration costs ~6 forward runs
(base + one per parameter for the Jacobian) plus a few lambda tests, so plan
for long wall-clock time given the multi-hour solve.
"""
import os
import numpy as np
import pandas as pd
import pyemu

HERE = os.path.dirname(os.path.abspath(__file__))

PARAM_FILE = os.path.join(HERE, "pest_params.dat")
TPL_FILE   = os.path.join(HERE, "pest_params.dat.tpl")
OBS_CSV    = os.path.join(HERE, "obs_wells.csv")
SIM_OUT    = os.path.join(HERE, "sim_heads.dat")
INS_FILE   = os.path.join(HERE, "sim_heads.dat.ins")
PST_FILE   = os.path.join(HERE, "calib.pst")

# ---------------------------------------------------------------------------
# Parameter definitions: (config name, pest name, init, lower, upper, transform)
# Bounds chosen around the documented Testing_1..3 calibration history.
# ---------------------------------------------------------------------------
PARAMS = [
    # config var            pest name    init   lower   upper  transform
    ("RCH_MULT",            "rch_mult",   0.45,  0.20,   0.90,  "log"),
    ("KV_ANISOTROPY_RATIO", "kv_aniso",  10.0,   1.0,  100.0,  "log"),
    ("GHB_COND_MULT",       "ghb_mult",   0.5,   0.05,   5.0,  "log"),
    ("DRN_COND_MULT",       "drn_mult",   1.0,   0.10,  10.0,  "log"),
    ("DRN_DEPTH_M",         "drn_depth",  2.0,   0.50,  10.0,  "none"),
]

# ---------------------------------------------------------------------------
# 1. TEMPLATE FILE  (writes pest_params.dat)
#    Left column keeps the literal config-var name; PEST fills the value field
#    between the ~ markers.  config.py reads "name value" per line.
# ---------------------------------------------------------------------------
with open(TPL_FILE, "w") as f:
    f.write("ptf ~\n")
    f.write("# written by PEST++; read by config.py via GLB_PEST_PARAMS\n")
    for cfg_name, pst_name, *_ in PARAMS:
        f.write(f"{cfg_name:<22}~ {pst_name:^14} ~\n")
print("wrote", TPL_FILE)

# ---------------------------------------------------------------------------
# 2. INSTRUCTION FILE  (reads sim_heads.dat)
#    sim_heads.dat lines are "obsname value" in obs_wells.csv order.
#    For each line: l1 advances one line, w skips the obsname token,
#    !name! reads the numeric value.
# ---------------------------------------------------------------------------
obs = pd.read_csv(OBS_CSV)
obs["obsname"] = obs["obsname"].astype(str)
with open(INS_FILE, "w") as f:
    f.write("pif ~\n")
    for name in obs["obsname"]:
        f.write(f"l1 w !{name}!\n")
print(f"wrote {INS_FILE}  ({len(obs)} observations)")

# A placeholder output file so from_io_files can validate the ins parsing.
with open(SIM_OUT, "w") as f:
    for name, val in zip(obs["obsname"], obs["obs_head_m"]):
        f.write(f"{name}  {float(val):.6f}\n")

# ---------------------------------------------------------------------------
# 3. BUILD Pst FROM TPL/INS
# ---------------------------------------------------------------------------
pst = pyemu.Pst.from_io_files(
    tpl_files=[TPL_FILE], in_files=[PARAM_FILE],
    ins_files=[INS_FILE], out_files=[SIM_OUT],
    pst_path=".",
)

# -- parameters --
pdata = pst.parameter_data
for cfg_name, pst_name, init, lo, hi, tr in PARAMS:
    m = pdata.parnme == pst_name
    pdata.loc[m, "parval1"]  = init
    pdata.loc[m, "parlbnd"]  = lo
    pdata.loc[m, "parubnd"]  = hi
    pdata.loc[m, "partrans"] = tr
    pdata.loc[m, "pargp"]    = "calib"
    pdata.loc[m, "scale"]    = 1.0
    pdata.loc[m, "offset"]   = 0.0

# -- observations: value = observed head, grouped by layer --
# WEIGHT_MODE:
#   "layer_balanced" : every layer group contributes equally to phi, so the
#                      deep bedrock (Layer 5, few wells, worst fit) is not
#                      drowned out by the shallow layers (many wells).
#                      weight_g = sqrt( (N_total / n_groups) / n_group )
#   "uniform"        : weight = 1 for every well (objective ~ total RMSE,
#                      dominated by the most-sampled shallow layers).
WEIGHT_MODE = "layer_balanced"

odata = pst.observation_data
odata = odata.set_index("obsnme", drop=False)
obs_idx = obs.set_index("obsname")

odata.loc[obs_idx.index, "obsval"] = obs_idx["obs_head_m"].astype(float).values
odata.loc[obs_idx.index, "obgnme"] = [f"hd_lay{int(l)}" for l in obs_idx["layer"].values]

if WEIGHT_MODE == "layer_balanced":
    counts = obs.groupby("layer").size()
    n_total, n_groups = len(obs), len(counts)
    w_by_layer = {lay: float(np.sqrt((n_total / n_groups) / cnt))
                  for lay, cnt in counts.items()}
    odata.loc[obs_idx.index, "weight"] = [w_by_layer[int(l)] for l in obs_idx["layer"].values]
    print("layer weights:", {int(k): round(v, 3) for k, v in w_by_layer.items()})
else:
    odata.loc[obs_idx.index, "weight"] = 1.0

pst.observation_data = odata.reset_index(drop=True)

# ---------------------------------------------------------------------------
# 4. MODEL COMMAND + CONTROL OPTIONS
# ---------------------------------------------------------------------------
pst.model_command = ["run_forward.bat"]

# Gauss-Levenberg-Marquardt controls
pst.control_data.noptmax = 0        # 0 = run once & check the .pst is valid.
                                    # Set to ~10 for a real calibration.
pst.control_data.phiredstp = 0.01   # stop if phi improves < 1% ...
pst.control_data.nphistp   = 3      # ... for 3 consecutive iterations
pst.control_data.nphinored = 3
pst.control_data.relparstp = 0.01
pst.control_data.nrelpar   = 3

# pestpp-glm: forward-difference Jacobian (5 runs/iter), a few lambdas
pst.pestpp_options["forgive_unknown_args"] = True
pst.pestpp_options["lambdas"] = [0.1, 1.0, 10.0]
pst.pestpp_options["max_run_fail"] = 1

pst.write(PST_FILE, version=2)
print("\nwrote", PST_FILE)
print(f"  parameters : {pst.npar}")
print(f"  observations: {pst.nobs}  (nnz weighted: {pst.nnz_obs})")
print("\nNEXT:")
print("  1) Test a single forward run :  pestpp-glm calib.pst   (noptmax=0)")
print("  2) Then set control_data.noptmax = 10 and re-run build_pest.py,")
print("     or edit calib.pst directly, and launch the real calibration.")
