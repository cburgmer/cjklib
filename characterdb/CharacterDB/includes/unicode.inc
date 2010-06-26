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
	$expanded = iconv("UTF-8", "UTF-32LE", $char);
	$codes = unpack("V*", $expanded);
	if (count($codes) > 1)
		return -1;
	else
		return $codes[1];
}

/**
 * Get a character for the given Unicode codepoint.
 */
function unichr($codepoint) {
	$character = pack("V", $codepoint);
	return iconv("UTF-32LE", "UTF-8", $character);
}
?>
