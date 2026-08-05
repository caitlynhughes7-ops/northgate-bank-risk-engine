/*--------------------------------------------------------------------------
  m_forward_looking_overlay.sas
  Post model management overlay by segment, as agreed with the CFO.
  Overlay factors are reviewed quarterly by the Provisions Committee.
--------------------------------------------------------------------------*/
%macro fli_overlay(inds=, outds=stg.overlay);
  %log_step(fli_overlay);

  data &outds;
    set &inds;
    /* Provisions Committee Dec-2023: cost of living overlay retained on
       unsecured, released on secured.                                   */
    select (SEGMENT);
      when ('CREDIT_CARD')   OVERLAY_FACTOR = 1.15;
      when ('OVERDRAFT')     OVERLAY_FACTOR = 1.15;
      when ('PERSONAL_LOAN') OVERLAY_FACTOR = 1.10;
      when ('SME_TERM')      OVERLAY_FACTOR = 1.05;
      otherwise              OVERLAY_FACTOR = 1.00;
    end;
  run;
%mend;
