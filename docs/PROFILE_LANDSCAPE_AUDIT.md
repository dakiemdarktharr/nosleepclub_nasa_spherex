# Independent profile-landscape audit

This audit checks the saved results of profile protocol
`704e3efc806dddef7906b032ba917745f80442a1` after all 112 journal records are
terminal. It opens no assessment journal, fits no positions, updates no Huber
weights, draws no noise and queries no new sky. This audit protocol and its
source/test hashes are recorded in the receipt and each resumable checkpoint.

The audit verifies the frozen source/input inventory, design, both upstream
journal digests, all 112 identities and checksums, baseline/corrected input
checksums and the original failures. For completed cells it reconstructs the
saved native data, errors, mask, neighbor IDs/design, baseline or corrected
PSF and the selected saved Huber weight vector. At fixed positions it solves
weighted linear coefficients with independently normalized NumPy least squares;
it never calls the study's profile, linear profile, grid, probe or connectivity
implementations. Same-arm saved point/final-start objective replays are checked
against both saved and independently calculated values.

Every global grid is checked for its 51×51 axes, finite nonnegative costs,
explicit missing-node records, bounds and 4/8-connectivity. Every focus local
grid receives the same checks for its 21×21 axes and recorded origin. Every
saved probe retains its expected source position, origin and three step records.
Independent WLS replays exactly the Cartesian global indices **0, 12, 25, 38,
50**, local indices **0, 10, 20**, and the nine-point stencil at both saved fit
positions for each step **0.004, 0.002, 0.001**. Missing selected points are
replayed as failures and must agree. At the two saved positions the audit checks
both gradients, full cost Hessian, Gauss–Newton matrix, eigenvalues, Jacobian
norms, rank and scaled condition; it does not merely compare a summary.

Predeclared comparison tolerances are relative `1e-9`, absolute `1e-8` for
costs; objective binding to the original fit uses the study's `1e-10` relative
and absolute tolerance. Probe derivatives use relative `1e-5`, absolute `1e-6`,
except the cost Hessian and its eigenvalues use absolute `1e-3` to allow
roundoff amplified by second differencing at 0.001 pixel. Axes use absolute
`1e-12`. Rank and all discrete identities are exact. These are numerical
cross-implementation tolerances, not stationarity or science acceptance gates.

An independent checkpoint is written for every planned cell; pre-existing
missing inputs are recorded as such. A failed study cell with both inputs
available is explicitly unverified, and any comparison mismatch is a finding;
neither is silently skipped or counted as an audit pass. The audit receipt is
written once and binds the source/test/protocol hashes, frozen design and both
input journals, the full profile journal and audit checkpoint digest. Do not
overwrite a receipt or change audit code while its checkpoints are in use.

```powershell
.venv/Scripts/python.exe -m unittest tests.test_profile_landscape_audit -v
# Only after the two original shards have completed:
.venv/Scripts/python.exe -m scripts.audit_profile_landscape
```

Passing this computational audit does not establish physical PSF truth, source
validity, independent validation, scientific improvement or coverage. Sampled
topology can miss unsampled structures, and the original failed gate remains
failed. This process does not authorize opening the 252 deferred cells or new
fields.
