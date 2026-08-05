%macro derive_arrears(inds=stg.tape_mapped, outds=stg.tape_arrears);
  %log_step(derive_arrears);

  data &outds;
    set &inds;
    length ARREARS_BUCKET $8;
    select;
      when (DPD_N = 0)                 ARREARS_BUCKET = '0';
      when (1  <= DPD_N <= 29)         ARREARS_BUCKET = '1-29';
      when (30 <= DPD_N <= 59)         ARREARS_BUCKET = '30-59';
      when (60 <= DPD_N <= 89)         ARREARS_BUCKET = '60-89';
      when (DPD_N >= 90)               ARREARS_BUCKET = '90+';
      otherwise                        ARREARS_BUCKET = 'UNK';
    end;

    /* part-month adjustment, see CHANGELOG v3.1 */
    if ARREARS_BUCKET = '1-29' and MONTHLY_PAYMENT > 0
       and DRAWN_BAL > 0
       and (DPD_N * MONTHLY_PAYMENT) / DRAWN_BAL < 0.001 then ARREARS_BUCKET = '0';
  run;
%mend;
