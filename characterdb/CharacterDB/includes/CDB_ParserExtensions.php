<?php
/**
 * This file contains code that affects parsing CharacterDB syntax.
 * @file
 * @author Christoph Burgmer
 */
global $cdbgIP;
include_once($cdbgIP . '/includes/unicode.inc');
include_once($cdbgIP . '/includes/CDB_StrokeOrder.inc');
include_once($cdbgIP . '/includes/CDB_Decomposition.inc');

/**
 * Static class to collect all functions related to parsing wiki text in
 *  CharacterDB.
 */
class CDBParserExtensions {

	/**
	 * This hook registers parser functions to the given parser.
	 */
	public static function registerParserFunctions(&$parser) {
		$parser->setFunctionHook( 'decomposition', array('CDBParserExtensions','doDecomposition') );
		$parser->setFunctionHook( 'components', array('CDBParserExtensions','doComponents') );
		$parser->setFunctionHook( 'allcomponents', array('CDBParserExtensions','doAllComponents') );
//		$parser->setFunctionHook( 'strokecount', array('CDBParserExtensions','doStrokeCount') );
		$parser->setFunctionHook( 'strokeorder', array('CDBParserExtensions','doStrokeOrder') );
		$parser->setFunctionHook( 'strokeordererror', array('CDBParserExtensions','doStrokeOrderError') );
		$parser->setFunctionHook( 'stroketoform', array('CDBParserExtensions','doStrokeToForm') );
		$parser->setFunctionHook( 'codepoint', array('CDBParserExtensions','doCodepoint') );
		$parser->setFunctionHook( 'codepointhex', array('CDBParserExtensions','doCodepointHex') );
		$parser->setFunctionHook( 'fromcodepoint', array('CDBParserExtensions','doFromCodepoint') );

		$counter = new Counter();
		$parser->setFunctionHook( 'counter', array(&$counter, 'doCounter') );
		return true; // always return true, in order not to stop MW's hook processing!
	}

	/**
	 * Function for handling the {{\#decomposition }} parser function.
	 */
	static public function doDecomposition($parser, $decomposition) {
		return CDBDecomposition::markupDecomposition($decomposition);
	}

	/**
	 * Function for handling the {{\#components }} parser function.
	 */
	static public function doComponents($parser, $decompositions) {
		return CDBDecomposition::getMainComponents($decompositions);
	}

	/**
	 * Function for handling the {{\#components }} parser function.
	 */
	static public function doAllComponents($parser, $decompositions) {
		return CDBDecomposition::getAllComponents($decompositions);
	}

	/**
	 * Function for handling the {{\#strokecount }} parser function.
	 */
/*	static public function doStrokeCount($parser, $strokeorder) {
		if (preg_match('/^\s*$/', $strokeorder))
		    return '';

		$strokes = preg_split("/[ -]/", $strokeorder);
		return strval(count($strokes));
	}*/

	/**
	 * Function for handling the {{\#strokeorder }} parser function.
	 */
	static public function doStrokeOrder($parser, $decompositions) {
		$decomp_list = explode("\n", $decompositions);
		$strokeorder = '';
		$strokes = 0;
		foreach ($decomp_list as $decomp) {
			$so = CDBStrokeOrder::getStrokeOrder($decomp);

			// check if stroke order not deducible
			if ($so == '')
				continue;
			// check if decomposition was valid
			if ($so == -1)
				return "ERROR: invalid decomposition";
                        $s = preg_split("/[ -]/", $so);
			// check each decomposition reaches same stroke order, compare strokes as separators might vary
			if ($strokeorder != '' && $strokes != $s)
				return "ERROR: ambiguous stroke order";

			$strokeorder = $so;
			$strokes = $s;
		}
		return $strokeorder;
	}

	/**
	 * Function for handling the {{\#strokeordererror }} parser function.
	 */
	static public function doStrokeOrderError($parser, $decompositions) {
		$decomp_list = explode("\n", $decompositions);
		foreach ($decomp_list as $decomp) {
		        // TODO don't stop if rule can't be found for first decomposition, the second one might hold one
			$error = CDBStrokeOrder::getStrokeOrderError($decomp);

			// check if stroke order not deducible
			if ($error != '')
				return $error;
		}
		return '';
	}

	/**
	 * Function for handling the {{\#stroketoform }} parser function.
	 */
	static public function doStrokeToForm($parser, $strokeorder) {
		return CDBStrokeOrder::getUnicodeFormsForStrokeNames($strokeorder);
	}

	/**
	 * Function for handling the {{\#codepoint }} parser function.
	 */
	static public function doCodepoint($parser, $character) {
		$value = uniord($character);
		if ($value === -1) {
			return "ERROR: invalid Unicode string";
		}
		return strval($value);
	}

	/**
	 * Function for handling the {{\#codepointhex }} parser function.
	 */
	static public function doCodepointHex($parser, $character) {
		$value = uniord($character);
		if ($value === -1) {
			return "ERROR: invalid Unicode string";
		}
		return dechex($value);
	}

	/**
	 * Function for handling the {{\#fromcodepoint }} parser function.
	 */
	static public function doFromCodepoint($parser, $codepoint, $base=10) {
		if (!is_numeric($base))
			$base = 10;
		$value = intval($codepoint, $base);
		if ($value < 1) {
			return "ERROR: invalid codepoint";
		}
		return unichr($value);
	}

}

class Counter {
	private static $count = 0;

	/**
	 * Function for handling the {{\#counter }} parser function.
	 */
	public function doCounter($parser) {
		$num = self::$count++;
		return strval($num);
	}
}
