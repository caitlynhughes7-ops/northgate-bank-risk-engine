%macro map_product_hierarchy(inds=stg.tape_clean, outds=stg.tape_mapped);
  %log_step(map_product_hierarchy);

  proc import datafile="&BASE./config/rules/product_hierarchy.csv"
       out=stg.prod_hier dbms=csv replace; getnames=yes; run;

  proc sql;
    create table &outds as
    select t.*,
           h.SEGMENT       as SEGMENT,
           h.SECURED_FLAG  as SECURED_FLAG,
           h.PROD_DESC     as PROD_DESC
    from &inds as t
    left join stg.prod_hier as h
      on t.PROD_CD = h.PROD_CD;
  quit;

  /* unmapped products are reported but not rejected - Finance requirement */
  proc sql noprint;
    select count(*) into :n_unmapped from &outds where SEGMENT is null;
  quit;
  %if &n_unmapped > 0 %then %put WARNING: [ECL] &n_unmapped exposures with unmapped PROD_CD;
%mend;
