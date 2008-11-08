CREATE TABLE LocaleCharacterVariant (
  ChineseCharacter CHAR(1) NOT NULL,        -- Chinese character (includes
                                            -- radical forms)
  ZVariant INTEGER NOT NULL DEFAULT 0,      -- Z-variant of character
  Locale VARCHAR(6) NOT NULL DEFAULT '',    -- Locale (T) traditional,
                                            --  (C) simplified Chinese,
                                            --  (J) Japanese,
                                            --  (K) Korean, (V) Vietnamese
  PRIMARY KEY (ChineseCharacter, Locale),
  UNIQUE (ChineseCharacter, ZVariant)
);
