/ Build a NEW date-partitioned HDB from the normalized TSV export.
/ Usage: q -q build_bars_hdb.q -input /path/bars.tsv -out /blue/group/gqh-kdb/version-001

opts:.Q.opt .z.x;
if[not `input in key opts; 2 "missing -input"; exit 2];
if[not `out in key opts; 2 "missing -out"; exit 2];
if[not `expected in key opts; 2 "missing -expected row count"; exit 2];
input:first opts`input;
out:first opts`out;
expected:"J"$first opts`expected;
outdir:hsym `$out;
if[0<count key outdir; 2 "refusing to build into a non-empty output directory"; exit 2];

schema:"*SSSJJJJJJ*";
raw:(schema; enlist "\t") 0: input;
if[0=count raw; 2 "empty TSV"; exit 3];

bars:flip `date`sym`source_id`batch_sha256`row_index`open_px_e8usd`high_px_e8usd`low_px_e8usd`close_px_e8usd`volume`row_sha256!
  (`date$raw`date; raw`sym; raw`source_id; raw`batch_sha256; "J"$raw`row_index;
   "J"$raw`open_px_e8usd; "J"$raw`high_px_e8usd; "J"$raw`low_px_e8usd; "J"$raw`close_px_e8usd;
   "J"$raw`volume; raw`row_sha256);

if[0=count bars; 2 "no normalized rows"; exit 3];
if[count bars<>expected; 2 "input row count differs from export manifest"; exit 4];
if[any null bars`date; 2 "null/invalid date"; exit 4];
if[any null bars`sym; 2 "null symbol"; exit 4];
if[any bars`high_px_e8usd<max each flip (bars`open_px_e8usd;bars`close_px_e8usd;bars`low_px_e8usd); 2 "high invariant failed"; exit 4];
if[any bars`low_px_e8usd>min each flip (bars`open_px_e8usd;bars`close_px_e8usd;bars`high_px_e8usd); 2 "low invariant failed"; exit 4];
if[any bars`volume<0; 2 "negative volume"; exit 4];
if[count bars<>count distinct select date,sym,source_id,batch_sha256 from bars; 2 "duplicate logical bar key"; exit 4];

/ The date column is represented by each on-disk partition directory in an HDB.
dates:asc distinct bars`date;
allbars:bars;
root:hsym `$out;
root:hsym `$((string root),"/");
do[count dates;
  d:dates i;
  bars:select sym,source_id,batch_sha256,row_index,open_px_e8usd,high_px_e8usd,low_px_e8usd,close_px_e8usd,volume,row_sha256 from allbars where date=d;
  bars:`sym`source_id xasc bars;
  .Q.dpft[root; d; `sym; `bars];
 ];

2 "HDB_BUILD_OK rows=",string count allbars," partitions=",string count dates," out=",out;
exit 0;
