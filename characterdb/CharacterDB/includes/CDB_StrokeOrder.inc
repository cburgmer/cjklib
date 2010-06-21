<?php
/**
 * This file contains code to calculate the stroke order from a decomposition.
 * @file
 * @author Christoph Burgmer
 */

/**
 * Exception raised when an invalid Ideographic Description Sequence is found.
 */
class InvalidIDSException extends Exception {}

/**
 * Exception raised if a request cannot be satisfied due to missing information.
 */
class NoInformationException extends Exception {}

/**
 * Static class to calculate stroke order from a character's decomposition.
 */
class CDBStrokeOrder {
	private static $binary_IDS_Ops = array('⿰', '⿱', '⿴', '⿵', '⿶', '⿷', '⿸', '⿹', '⿺', '⿻');
	private static $trinary_IDS_Ops = array('⿲', '⿳');

	/**
	 * Main function.
	 */
	public static function getStrokeOrder($decomposition) {
		$matches = array();
		preg_match_all('/[⿰⿱⿴⿵⿶⿷⿸⿹⿺⿻⿲⿳]|[^⿰⿱⿴⿵⿶⿷⿸⿹⿺⿻⿲⿳\d](?:\\/\d+)?/u', $decomposition, $matches);
		$decomp = $matches[0];
		try {
			$pos = 0;
			$strokeorder = CDBStrokeOrder::getStrokeOrderRecursive($decomp, $pos);
			if ($pos != count($decomp))
				throw new InvalidIDSException('Invalid IDS at ' . strval($pos));
			return $strokeorder;
		} catch (InvalidIDSException $e) {
			return -1;
		} catch (NoInformationException $e) {
			return '';
		}
	}

	/**
	 * Get reason why stroke order cannot be calulated, similar to getStrokeOrder().
	 */
	public static function getStrokeOrderError($decomposition) {
		$matches = array();
		preg_match_all('/[⿰⿱⿴⿵⿶⿷⿸⿹⿺⿻⿲⿳]|[^⿰⿱⿴⿵⿶⿷⿸⿹⿺⿻⿲⿳\d](?:\\/\d+)?/u', $decomposition, $matches);
		$decomp = $matches[0];
		try {
			$pos = 0;
			$strokeorder = CDBStrokeOrder::getStrokeOrderRecursive($decomp, $pos);
			if ($pos != count($decomp))
				throw new InvalidIDSException('Invalid IDS at ' . strval($pos));
		} catch (Exception $e) {
			return $e->getMessage();
		}
		return '';
	}

	/**
	 * Recursively calculate stroke order.
	 */
	private static function getStrokeOrderRecursive($decomposition, &$pos) {
		if ($pos >= count($decomposition))
			throw new InvalidIDSException('Invalid IDS at ' . strval($pos));

		if (in_array($decomposition[$pos], self::$binary_IDS_Ops)) {
			// binary IDS
			$ids_op = $decomposition[$pos];
			$pos++;

			$components = array();
			$strokeorders = array();

			$components[] = $decomposition[$pos];
			$strokeorders[] = CDBStrokeOrder::getStrokeOrderRecursive($decomposition, $pos);

			$components[] = $decomposition[$pos];
			$strokeorders[] = CDBStrokeOrder::getStrokeOrderRecursive($decomposition, $pos);

			return CDBStrokeOrder::combineStrokeOrders($ids_op, $components, $strokeorders);
		} else if (in_array($decomposition[$pos], self::$trinary_IDS_Ops)) {
			// trinary IDS
			$ids_op = $decomposition[$pos];
			$pos++;

			$components = array();
			$strokeorders = array();

			$components[] = $decomposition[$pos];
			$strokeorders[] = CDBStrokeOrder::getStrokeOrderRecursive($decomposition, $pos);

			$components[] = $decomposition[$pos];
			$strokeorders[] = CDBStrokeOrder::getStrokeOrderRecursive($decomposition, $pos);

			$components[] = $decomposition[$pos];
			$strokeorders[] = CDBStrokeOrder::getStrokeOrderRecursive($decomposition, $pos);

			return CDBStrokeOrder::combineStrokeOrders($ids_op, $components, $strokeorders);
		} else {
			// component
			$strokeorder = CDBStrokeOrder::lookupStrokeOrder($decomposition[$pos]);
			$pos++;
			return $strokeorder;
		}
	}

	/**
	 * Lookup stroke order of component.
	 */
	private static function lookupStrokeOrder($component) {
		if (!preg_match('/^.\\/\d+$/u', $component))
			throw new InvalidIDSException('Invalid glyph at for ' . $component);

		$title = Title::newFromText($component, $defaultNamespace=NS_MAIN);
		$property = SMWPropertyValue::makeUserProperty('StrokeOrder');
		$getpropval = smwfGetStore()->getPropertyValues($title, $property, $requestoptions=null, $outputformat= '');
		if ($getpropval && count($getpropval) > 0)
			return $getpropval[0]->getshortwikitext();
		else
			throw new NoInformationException('No stroke order for component ' . $component);

	}

	/**
	 * Combine stroke order of components based on a set of rules, yielding the stroke order of the parent character.
	 */
	private static function combineStrokeOrders($idsoperator, $components, $strokeorders) {
		$plaintext_rules = wfMsg('cdb-strokeorder-rules');

			//$title = Title::newFromText('CharacterDB:StrokeOrderRules');
			//$article = MediaWiki::articleFromTitle($title);
			// TODO self::$rules = Article::getRawText();
		$rule_list = explode("\n", $plaintext_rules);

		$idsop_length = strlen($idsoperator);
		foreach ($rule_list as $rule) {
			// check if ids operator applies to rule
			if (!(strcmp(substr($rule, 0, $idsop_length), $idsoperator)===0)) {
				continue;
			}

			$rule_parts = array();
			if (!preg_match('/^([⿰⿱⿴⿵⿶⿷⿸⿹⿺⿻⿲⿳])\s*((?:[123]|[A-Z]+)(?:(?:-| )(?:[123]|[A-Z]+))+)((?:\s*\\|\s*[123]\s+(?:is|has)\s+[^\\|]+)*)$/u', $rule, $rule_parts))
			    throw new Exception('Error parsing rule ' . $rule);

			$matches = 1;
			// get filters and apply
			$filter_list = array();
			preg_match_all('/\s*\\|\s*([123]\s+(?:is|has)\s+[^\\|]+)/u', $rule_parts[3], $filter_list);
			foreach ($filter_list[1] as $filter) {
				$filter_parts = array();
				// parse: component index, relationship, value(s)
				preg_match('/^([123])\s+(is|has)\s+(.+?)\s*$/u', $filter, $filter_parts);
				$comp_idx = $filter_parts[1] - 1;
				$filter_type = $filter_parts[2];
				$filter_val = $filter_parts[3];

				if ($filter_type == 'is') {
					// check that component matches given character list
					if (!CDBStrokeOrder::matchesCharacters( $components[$comp_idx], $strokeorders[$comp_idx], $filter_val)) {
						$matches = 0;
						break;
					}
				} else if ($filter_type == 'has') {
					// check that component has given stroke order
					if (!CDBStrokeOrder::matchesStrokeOrder( $components[$comp_idx], $strokeorders[$comp_idx], $filter_val)) {
						$matches = 0;
						break;
					}
				}
				
			}

			// check if rule matched and build stroke order
			if ($matches) {
				return str_replace(array(1, 2, 3), $strokeorders, $rule_parts[2]);
			}
		}

		throw new NoInformationException('No rule found to parse decomposition');
	}


	/**
	 * Filter matching character list.
	 */
	private static function matchesCharacters($component, $strokeorder, $value) {
		// get character from component glyph
		$comp = mb_substr($component, 0, 1, 'UTF-8');
		return mb_strstr($value, $comp);
	}

	/**
	 * Filter matching stroke order.
	 */
	private static function matchesStrokeOrder($component, $strokeorder, $value) {
		return preg_split("/[ -]/", $value) == preg_split("/[ -]/", $strokeorder);
	}

	/**
	 * Map stroke names to Unicode stroke forms.
	 */
	public static function getUnicodeFormsForStrokeNames($strokeorder) {
		// read mapping
		$mapping_table_content = wfMsg('cdb-stroke-mapping');
		$entry_list = explode("\n", $mapping_table_content);

		$mapping_table = array();
		$matches = array();
		foreach ($entry_list as $entry) {
			if (preg_match("/^(\w+)\s*,\s*(.)$/u", $entry, $matches)) {
				$mapping_table[$matches[1]] = $matches[2];
			}
		}

		// apply mapping
		$strokes = array();
		foreach (preg_split("/[ -]/", $strokeorder) as $stroke_name)
			if (array_key_exists($stroke_name, $mapping_table))
				$strokes[] = $mapping_table[$stroke_name];
			else
				$strokes[] = $stroke_name;

		return join($strokes);
	}

}
?>
