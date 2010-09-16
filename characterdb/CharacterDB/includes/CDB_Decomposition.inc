<?php
/**
 * This file contains code to work with character decompositions.
 * @file
 * @author Christoph Burgmer
 */

/**
 * Exception raised when an invalid Glyph is found.
 */
class InvalidGlyphException extends Exception {}

/**
 * Static class to do all the decomposition handling.
 */
class CDBDecomposition {
	/**
	 * Add markup to the given decomposition.
	 */
	public static function markupDecomposition($decomposition) {
		return preg_replace('/[^⿰⿱⿴⿵⿶⿷⿸⿹⿺⿻⿲⿳\d](\\/\d+)?/u', '[[${0}]]', $decomposition);
	}

	/**
	 * Get main components for the given decompositions.
	 */
	public static function getMainComponents($decompositions) {
		$decomp_list = explode("\n", $decompositions);

		$components = array();
		foreach ($decomp_list as $decomp) {
		    $matches = array();
		    preg_match_all('/[^⿰⿱⿴⿵⿶⿷⿸⿹⿺⿻⿲⿳\d](\\/\d+)?/u', $decomp, $matches);
		    $components = array_merge($components, $matches[0]);
		}
		return join(",", array_unique($components));
	}

	/**
	 * Get all components (recursively) for the given decompositions.
	 */
	public static function getAllComponents($decompositions) {
		$decomp_list = explode("\n", $decompositions);

		$components = array();
		CDBDecomposition::getAllComponentsRecursive($decomp_list, $components);
		return join(",", array_unique($components));
	}

	/**
	 * Recursively go through decompositions for all components.
	 */
	public static function getAllComponentsRecursive($decomp_list, &$components) {
		$matches = array();
		foreach ($decomp_list as $decomp) {
			preg_match_all('/[^⿰⿱⿴⿵⿶⿷⿸⿹⿺⿻⿲⿳\d](\\/\d+)?/u', $decomp, $matches);
			foreach ($matches[0] as $comp) {
				$components[] = $comp;
				try {
					$sub_decomp_list = CDBDecomposition::lookupDecomposition($comp);
					CDBDecomposition::getAllComponentsRecursive($sub_decomp_list, $components);
				} catch (InvalidGlyphException $e) {}

			}
		}
	}

	/**
	 * Lookup decompositions of character.
	 */
        public static function lookupDecomposition($character) {
		if (!preg_match('/^.\\/\d+$/u', $character))
			throw new InvalidGlyphException('Invalid glyph at for ' . $character);

		$title = Title::newFromText($character, $defaultNamespace=NS_MAIN);
		$property = SMWPropertyValue::makeUserProperty('Decomposition');
		$getpropval = smwfGetStore()->getPropertyValues($title, $property, $requestoptions=null, $outputformat= '');

                $decompositions = array();
		foreach ($getpropval as $val) {
			if (!is_null($val) && method_exists($val, 'getDVs')) {
				$recordValues = $val->getDVs();
				$decompositions[] = $recordValues[0]->getshortwikitext();
			}
		}
		return $decompositions;
        }

}
?>
