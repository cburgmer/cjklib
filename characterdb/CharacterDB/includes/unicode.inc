<?php
/**
 * Provide unicode support methods.
 * @file
 * @author Christoph Burgmer
 */

/**
 * Get the Unicode codepoint of the given character. Returns -1 if value is not a single character.
 */
function uniord($char) {
	$expanded = iconv("UTF-8", "UTF-32", $char);
	$codes = unpack("L*", $expanded);
	if (count($codes) > 2)
		return -1;
	else
		return $codes[2];
}

/**
 * Get a character for the given Unicode codepoint.
 */
function unichr($codepoint) {
	$character = pack("L", $codepoint);
	return iconv("UTF-32", "UTF-8", $character);
}
?>
