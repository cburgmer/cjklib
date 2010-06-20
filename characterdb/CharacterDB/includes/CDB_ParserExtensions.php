<?php
/**
 * This file contains code that affects parsing CharacterDB syntax.
 * @file
 * @author Christoph Burgmer
 */
global $cdbgIP;
include_once($cdbgIP . '/includes/php-utf8/utf8.inc');
include_once($cdbgIP . '/includes/CDB_StrokeOrder.inc');

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
		$parser->setFunctionHook( 'strokecount', array('CDBParserExtensions','doStrokeCount') );
		$parser->setFunctionHook( 'strokeorder', array('CDBParserExtensions','doStrokeOrder') );
		$parser->setFunctionHook( 'strokeordererror', array('CDBParserExtensions','doStrokeOrderError') );
		$parser->setFunctionHook( 'codepoint', array('CDBParserExtensions','doCodepoint') );
		$parser->setFunctionHook( 'codepointhex', array('CDBParserExtensions','doCodepointHex') );
		$counter = new Counter();
		$parser->setFunctionHook( 'counter', array(&$counter, 'doCounter') );
		return true; // always return true, in order not to stop MW's hook processing!
	}

	/**
	 * Function for handling the {{\#decomposition }} parser function.
	 */
	static public function doDecomposition($parser, $decomposition) {
		return preg_replace('/[^⿰⿱⿴⿵⿶⿷⿸⿹⿺⿻⿲⿳\d](\\/\d+)?/u', '[[${0}]]', $decomposition);
	}

	/**
	 * Function for handling the {{\#strokecount }} parser function.
	 */
	static public function doStrokeCount($parser, $strokeorder) {
		if (preg_match('/^\w*$/', $strokeorder))
		    return '';

		$strokes = preg_split("/[ -]/", $strokeorder);
		return strval(count($strokes));
	}

        /**
         * Function for handling the {{\#strokeorder }} parser function.
         */
        static public function doStrokeOrder($parser, $decompositions) {
		$decomp_list = explode("\n", $decompositions);
		$strokeorder = '';
		foreach ($decomp_list as $decomp) {
			$so = CDBStrokeOrder::getStrokeOrder($decomp);

			// check if stroke order not deducible
			if ($so == '')
				continue;
			// check if decomposition was valid
			if ($so == -1)
				return "ERROR: invalid decomposition";
			// check each decomposition reaches same stroke order
			if ($strokeorder != '' && $strokeorder != $so)
				return "ERROR: ambiguous stroke order";

			$strokeorder = $so;
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
	 * Function for handling the {{\#codepoint }} parser function.
	 */
	static public function doCodepoint($parser, $character) {
		$value = utf8ToUnicode($character);
		if (! $value) {
			return "ERROR: invalid Unicode string";
		}
		return strval($value[0]);
	}

	/**
	 * Function for handling the {{\#codepointhex }} parser function.
	 */
	static public function doCodepointHex($parser, $character) {
		$value = utf8ToUnicode($character);
		if (! $value) {
			return "ERROR: invalid Unicode string";
		}
		return dechex($value[0]);
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
