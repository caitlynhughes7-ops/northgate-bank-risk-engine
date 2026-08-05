%macro lgd_unsecured(inds=stg.pd_pit, outds=stg.lgd_unsec);
  %log_step(lgd_unsecured);

  data &outds;
    set &inds;
    where SECURED_FLAG ne 'Y';

    /* segment LGD from internal recovery study (2021 refresh) */
    select (SEGMENT);
      when ('PERSONAL_LOAN') LGD_RAW = 0.62;
      when ('CREDIT_CARD')   LGD_RAW = 0.78;
      when ('OVERDRAFT')     LGD_RAW = 0.84;
      when ('SME_TERM')      LGD_RAW = 0.55;
      otherwise              LGD_RAW = 0.65;
    end;

    /* unsecured regulatory floor */
    LGD = max(LGD_RAW, 0.45);
  run;
%mend;
