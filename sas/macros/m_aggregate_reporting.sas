%macro aggregate_reporting(inds=stg.ecl_acct, outds=out.ecl_by_segment);
  %log_step(aggregate_reporting);

  proc sql;
    create table &outds as
    select SEGMENT,
           STAGE,
           count(*)      as N_EXPOSURES,
           sum(EAD)      as TOTAL_EAD  format=comma18.2,
           sum(ECL)      as TOTAL_ECL  format=comma18.2,
           case when sum(EAD) > 0 then sum(ECL)/sum(EAD) else 0 end
                         as COVERAGE   format=percent9.4
    from &inds
    group by SEGMENT, STAGE
    order by SEGMENT, STAGE;
  quit;
%mend;
