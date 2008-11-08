CREATE TABLE GRAbbreviation (
  ChineseCharacter VARCHAR(1),  -- Chinese character
  GR VARCHAR(9),                -- ethymological GR form
  GRAbbreviation VARCHAR(9),    -- abbreviated GR form
  UNIQUE(ChineseCharacter, GR, GRAbbreviation)
);
