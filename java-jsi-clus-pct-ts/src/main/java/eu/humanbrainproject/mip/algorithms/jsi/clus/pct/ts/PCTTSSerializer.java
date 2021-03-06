
package eu.humanbrainproject.mip.algorithms.jsi.clus.pct.ts;

import java.io.IOException;

import com.fasterxml.jackson.core.JsonGenerator;

import eu.humanbrainproject.mip.algorithms.jsi.serializers.pfa.ClusGenericSerializer;
import si.ijs.kt.clus.algo.tdidt.ClusNode;
import si.ijs.kt.clus.data.type.primitive.NominalAttrType;
import si.ijs.kt.clus.data.type.primitive.NumericAttrType;
import si.ijs.kt.clus.model.test.InverseNumericTest;
import si.ijs.kt.clus.model.test.NodeTest;
import si.ijs.kt.clus.model.test.NominalTest;
import si.ijs.kt.clus.model.test.NumericTest;
import si.ijs.kt.clus.model.test.SubsetTest;
import si.ijs.kt.clus.statistic.ClusStatistic;
import si.ijs.kt.clus.statistic.RegressionStat;

/**
 * @author Martin Breskvar
 *     <p>This class serializes a PCT for time-series
 */
public class PCTTSSerializer extends ClusGenericSerializer<ClusNode> {

  @Override
  public void writeModelConstants(ClusNode model, JsonGenerator jgen) throws IOException {}

  private void writePrediction(ClusStatistic stat, JsonGenerator jgen) throws IOException {
    // Regression stat
    RegressionStat rs = (RegressionStat) stat;
    NumericAttrType[] attrs = rs.getAttributes();

    if (attrs.length == 1) {
      jgen.writeNumber(rs.m_Means[0]);
    } else {
      jgen.writeStartObject();
      {
        jgen.writeStringField("type", "DependentVariables");
        jgen.writeObjectFieldStart("new");
        {
          for (int i = 0; i < attrs.length; i++) {
            jgen.writeNumberField(attrs[i].getName(), rs.m_Means[i]);
          }
        }
        jgen.writeEndObject();
      }
      jgen.writeEndObject();
    }
  }

  private void constructRecursive(ClusNode node, JsonGenerator jgen) throws IOException {
    NodeTest test = node.getTest();

    jgen.writeObjectFieldStart("if");
    {
      String symbol = "";
      String name = "input." + test.getType().getName();
      Object bound = null;

      if (test instanceof NumericTest) {
        bound = ((NumericTest) test).getBound();
        symbol = ">";
        if (test instanceof InverseNumericTest) {
          symbol = "<=";
        }
      } else if ((test instanceof SubsetTest && ((SubsetTest) test).getNbValues() == 1)
          || test instanceof NominalTest) {
        symbol = "==";

        if (test instanceof SubsetTest) {
          SubsetTest t = (SubsetTest) test;

          if (t.getType() instanceof NominalAttrType) {
            int idx = t.getValue(0);
            bound = ((NominalAttrType) t.getType()).getValue(idx);
          } else {
            // no luck, try to get value from string
            String b = test.getTestString();
            bound = b.substring(b.indexOf("=") + 1).trim();
          }
        } else {
          String b = ((NominalTest) test).getTestString();
          bound = b.substring(b.indexOf("=") + 1).trim();
        }
      }

      jgen.writeArrayFieldStart(symbol);
      {
        jgen.writeString(name);
        if (test instanceof NumericTest) {
          jgen.writeNumber((double) bound);
        } else {
          jgen.writeString((String) bound);
        }
      }
      jgen.writeEndArray();
    }
    jgen.writeEndObject();

    // then
    ClusNode child = (ClusNode) node.getChild(0);
    jgen.writeFieldName("then");
    if (!child.atBottomLevel()) {
      jgen.writeStartObject();
      {
        constructRecursive(child, jgen);
      }
      jgen.writeEndObject();
    } else {
      writePrediction(child.getTargetStat(), jgen);
    }

    // else
    child = (ClusNode) node.getChild(1);
    jgen.writeFieldName("else");
    if (!child.atBottomLevel()) {
      jgen.writeStartObject();
      {
        constructRecursive(child, jgen);
      }
      jgen.writeEndObject();
    } else {
      writePrediction(child.getTargetStat(), jgen);
    }
  }

  @Override
  public void writePfaAction(ClusNode model, JsonGenerator jgen) throws IOException {

    if (model.atBottomLevel()) {
      writePrediction(model.getTargetStat(), jgen);
    } else {
      jgen.writeStartObject();
      {
        constructRecursive(model, jgen);
      }
      jgen.writeEndObject();
    }
  }
}
