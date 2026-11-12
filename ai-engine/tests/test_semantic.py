import pytest
import os
@pytest.mark.skipif(os.getenv('EMBEDDING_MODE')=='lexical',reason='Explicit offline lexical test mode')
def test_semantic_retrieval():
    from app.retrieval import semantic_embed
    import numpy as np
    q=np.array(semantic_embed('What voltage powers this part?'))
    relevant=np.array(semantic_embed('The component supply operating range is 2.7 to 3.6 V.'))
    irrelevant=np.array(semantic_embed('The package is shipped in reels of one thousand units.'))
    assert len(q)==384
    assert q@relevant>q@irrelevant
