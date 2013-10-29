<xsl:stylesheet version="1.0" 
                xmlns:xsl="http://www.w3.org/1999/XSL/Transform"
                xmlns:atom="http://www.w3.org/2005/Atom"
                xmlns:app="http://www.w3.org/2007/app">

  <xsl:template match="/">
    <html>
      <body>
        <h1>Services</h1>
        <ul>
        <xsl:for-each select="app:service/app:workspace">
          <li>
            <xsl:value-of select="atom:title"/>
            <xsl:for-each select="app:collection">
              <ul>
                <li>
                  <p>
                    <a>
                      <xsl:attribute name="href">
                        <xsl:value-of select="@href"/>
                      </xsl:attribute>
                      <xsl:value-of select="atom:title"/>
                    </a>
                  </p>
                  <p>
                    Accepts:
                    <xsl:for-each select="app:accept">
                      <xsl:value-of select="."/>,
                    </xsl:for-each>
                  </p>
                </li>
              </ul>
            </xsl:for-each>
          </li>
        </xsl:for-each>
        </ul>
      </body>
    </html>
  </xsl:template>
</xsl:stylesheet>
