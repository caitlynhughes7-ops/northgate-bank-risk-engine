/*--------------------------------------------------------------------------
  run_month_end.sas
  Control-M entry point. Runs the ECL engine then the Board pack extract.
--------------------------------------------------------------------------*/
%include "run_ifrs9_ecl.sas";

/* Board pack extract - added 2023 for Pillar 3 template change */
proc sql;
  create table out.board_pack as
  select SEGMENT, sum(TOTAL_EAD) as EAD, sum(TOTAL_ECL) as ECL
  from out.ecl_by_segment group by SEGMENT;
quit;
