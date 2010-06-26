<?php
/**
 * Global functions for CharacterDB extensions.
 * @file
 */
define('CDB_VERSION','0.1');

function enableCharacterDBExtensions() {
	global $cdbgIP, $wgExtensionFunctions, $wgExtensionMessagesFiles, $wgAutoloadClasses;
	$wgExtensionFunctions[] = 'cdbfSetupExtension';

	///// Set up autoloading; essentially all classes should be autoloaded!
	$wgAutoloadClasses['CDBParserExtensions'] = $cdbgIP . '/includes/CDB_ParserExtensions.php';

	$wgExtensionMessagesFiles['CharacterDB'] = $cdbgIP . '/languages/CDB_Messages.php';

	return true;
}

/**
 * Do the actual intialisation of the extension. This is just a delayed init that makes sure
 * MediaWiki is set up properly before we add our stuff.
 *
 * The main things this function does are: register all hooks, set up extension credits, and
 * init some globals that are not for configuration settings.
 */
function cdbfSetupExtension() {
	wfProfileIn('cdbfSetupExtension (CDB)');
	global $cdbgIP;
	global $wgHooks, $wgExtensionCredits;
	global $sfgFormPrinter; // SemanticForms

	$wgHooks['OutputPageBeforeHTML'][] = 'cdbfRedirectMainSubpage';
	$wgHooks['ArticleSaveComplete'][] = 'cdbfPurgeMainSubpage';
	$wgHooks['LanguageGetMagic'][] = 'cdbfAddMagicWords'; // setup names for parser functions (needed here)
	$wgHooks['ParserFirstCallInit'][] = 'CDBParserExtensions::registerParserFunctions';
       // FIXME: Can be removed when new style magic words are used (introduced in r52503)
	///// credits (see "Special:Version") /////
	$wgExtensionCredits['parserhook'][]= array(
		'path' => __FILE__,
		'name' => 'CharacterDB Extensions',
		'version' => CDB_VERSION,
		'author'=> "Christoph Burgmer",
		'url' => 'http://characterdb.cjklib.org/',
		'descriptionmsg' => 'cdb-desc'
	);

	if ( $sfgFormPrinter ) {
		include_once($cdbgIP . '/includes/CDB_FormInputs.inc');
		$sfgFormPrinter->setInputTypeHook('decomposition', 'decompositionHTML', array());
	}

	wfProfileOut('cdbfSetupExtension (CDB)');
	return true;
}

/**
  * Set up (possibly localised) names for parser functions.
  * @todo Can be removed when new style magic words are used (introduced
in r52503)
  */
function cdbfAddMagicWords(&$magicWords, $langCode) {
	$magicWords['decomposition'] = array( 0, 'decomposition' );
	$magicWords['components']    = array( 0, 'components' );
	$magicWords['allcomponents'] = array( 0, 'allcomponents' );
//	$magicWords['strokecount']   = array( 0, 'strokecount' );
	$magicWords['strokeorder']   = array( 0, 'strokeorder' );
	$magicWords['strokeordererror']   = array( 0, 'strokeordererror' );
	$magicWords['stroketoform']  = array( 0, 'stroketoform' );
	$magicWords['codepoint']     = array( 0, 'codepoint' );
	$magicWords['codepointhex']  = array( 0, 'codepointhex' );
	$magicWords['counter']       = array( 0, 'counter' );
	return true;
}

function cdbfGetMainSubpage($title) {
	if ($title->getNamespace() != NS_MAIN)
		return true;
	if (!MWNamespace::hasSubpages($title->getNamespace()))
		return true;

	$parts = explode( '/', $title->getText() );
	return $parts[0];
}

function cdbfRedirectMainSubpage(&$out, &$text) {
	$title = $out->getTitle();
	$target = cdbfGetMainSubpage($title);

	if ($target != '' && $target != $title->getText()) {
		$targetTitle=Title::newFromText($target);
		$targetTitle->setFragment($title);
		$out->redirect($targetTitle->getFullURL(""));
		return false;
	}
	return true;
}

function cdbfPurgeMainSubpage($article, $user, $text, $summary, $isMinor, $isWatch, $section, $section, $flags, $revision, $baseRevId) {
	$title = $article->getTitle();
	$main = cdbfGetMainSubpage($title);

	if ($main != '' && $main != $title->getText()) {
	    $mainTitle=Title::newFromText($main);
	    $mainArticle = MediaWiki::articleFromTitle($mainTitle);
	    $mainArticle->doPurge();
	}
	return true;
}
