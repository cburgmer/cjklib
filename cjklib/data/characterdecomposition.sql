CREATE TABLE CharacterDecomposition (
  ChineseCharacter CHAR(1) NOT NULL,        -- Chinese character (includes
                                            --   radical forms)
  Decomposition VARCHAR(50) NOT NULL,       -- Decomposition into sub parts
  ZVariant INTEGER NOT NULL DEFAULT 0,      -- Z-variant of character
  SubIndex INTEGER NOT NULL DEFAULT 0,      -- additional index for uniqueness
  Flags VARCHAR(5) DEFAULT '',              -- Flags, (O) checked, (S) variant
                                            --   found only as sub part
  PRIMARY KEY (ChineseCharacter, ZVariant, SubIndex)
);
