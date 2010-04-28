<?php
/**
 * CharacterDB input types.
 * @file
 */

/*
 * Definition of input type "decomposition"
 */
function decompositionHTML ($cur_value, $input_name, $is_mandatory, $is_disabled, $other_args) {
	global $sfgTabIndex, $sfgFieldNum, $sfgJSValidationCalls;

	formsInputSetup();

	$className = ($is_mandatory) ? "createboxInput mandatoryField" : "createboxInput";
	if (array_key_exists('class', $other_args))
		$className .= " " . $other_args['class'];
	$input_id = "input_$sfgFieldNum";
	$info_id = "info_$sfgFieldNum";
	if (array_key_exists('size', $other_args)) {
		$size = $other_args['size'];
	} else {
		$size = 35;
	}

	if (! is_null($cur_value))
		$cur_value = htmlspecialchars($cur_value);

	$text =<<<END
		<input id="$input_id" tabindex="$sfgTabIndex" class="$className" name="$input_name" type="text" value="$cur_value" size="$size"
END;
	if ($is_disabled)
		$text .= " disabled";
	if (array_key_exists('maxlength', $other_args))
		$text .= ' maxlength="' . $other_args['maxlength'] . '"';
	$text .=<<<END
/>
	<span id="$info_id" class="errorMessage"></span>

END;

	$sfgJSValidationCalls[] = "validate_decomposition_string('$input_id', '$info_id')";

	return array($text, null);
}

/**
  * All the Javascript calls to validate the type of each form field
  */
function validationJavascript() {
	$cdb_bad_decomposition = Xml::escapeJsString(wfMsg('cdb_bad_decomposition'));

	$javascript_text =<<<END
function validate_decomposition_string(field_id, info_id) {
	if (!Array.prototype.indexOf) {
		Array.prototype.indexOf = function (obj, start) {
			for (var i = (start || 0); i < this.length; i++) {
				if (this[i] == obj) {
					return i;
				}
			}
			return -1;
		}
	}

	function checkDecomposition(string) {
		function walkString(idx) {
			if (idx >= string.length) {
				// error
				return string.length+1;
			} else if (IDS_BINARY.indexOf(string.charAt(idx)) >= 0) {
				idx = walkString(idx+1);
				idx = walkString(idx);
			} else if (IDS_TRINARY.indexOf(string.charAt(idx)) >= 0) {
				idx = walkString(idx+1);
				idx = walkString(idx);
				idx = walkString(idx);
			} else {
				var glyphRegex = /^.(\/\d+)?/;
				var results = glyphRegex.exec(string.substring(idx));
				if (results) {
					idx += results[0].length;
				} else {
					// error
					idx = string.length+1;
				}
			}
			return idx;
		}
		IDS_BINARY = ['⿰', '⿱', '⿴', '⿵', '⿶', '⿷', '⿸', '⿹', '⿺', '⿻'];
		IDS_TRINARY = ['⿲', '⿳'];
		return (!string) || (string.length > 2 && walkString(0) == string.length);
	}

	field = document.getElementById(field_id);
	if (field.value == '') {
		return true;
	} else {
		if (checkDecomposition(field.value)) {
			return true;
		} else {
			infobox = document.getElementById(info_id);
			infobox.innerHTML = "$cdb_bad_decomposition";
			return false;
		}
	}
}

END;
	return $javascript_text;
}

/*
 * Setup for input type regexp.
 * Adds the Javascript code used by all regexp filters.
 */
function formsInputSetup() {

	global $wgOut;

	static $hasRun = false;

	if (!$hasRun) {
		$hasRun=true;

		$wgOut->addInlineScript(validationJavascript());
	}
}
