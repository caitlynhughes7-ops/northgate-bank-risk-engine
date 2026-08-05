%macro export_disclosure(inds=out.ecl_by_segment, period=);
  %log_step(export_disclosure);

  proc export data=&inds
       outfile="&OUTBOUND./ecl_by_segment_&period..csv"
       dbms=csv replace;
  run;

  /* Finance GL feed - fixed width, do not reformat */
  data _null_;
    set &inds;
    file "&OUTBOUND./ECL_GL_FEED_&period..txt";
    put @1 SEGMENT $20. @21 STAGE z1. @22 TOTAL_ECL 18.2;
  run;
%mend;
