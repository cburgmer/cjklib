<?php
/**
 * This file contains code that affects parsing CharacterDB syntax.
 * @file
 * @author Christoph Burgmer
 */
global $cdbgIP;
include_once($cdbgIP . '/includes/php-utf8/utf8.inc');

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
		$parser->setFunctionHook( 'codepoint', array('CDBParserExtensions','doCodepoint') );
		$parser->setFunctionHook( 'codepointhex', array('CDBParserExtensions','doCodepointHex') );
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
		$strokes = preg_split("/[ -]/", $strokeorder);
		return strval(count($strokes));
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
